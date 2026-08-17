import json
import os
import re
from google import genai
from google.genai import types

from agent.prompts import REASON_PROMPT

# ==========================================
# LLM CLIENT
# ==========================================
def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)


def parse_json_response(response_text: str) -> dict:
    """
    Defensively parse JSON from LLM response.
    Strips markdown code fences if the LLM disobeys the strict format prompt.
    """
    clean_text = response_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    return json.loads(clean_text.strip())


# ==========================================
# PERCEIVE  —  Pure Python, no LLM
# ==========================================
def perceive(input_data: str) -> dict:
    """
    Parse and structure raw input. Extract intent, constraints,
    context, and any relevant signals from the user's input.
    
    `input_data` may be:
      - A plain text string (first iteration).
      - A JSON-encoded state dict containing 'text_to_process' and
        'next_instruction' (fed back from the previous reflect call).
    
    Returns a structured observation dict.
    """
    # --- Feed reflect's output back into perceive ---
    # If the caller passes a JSON state (from the loop), unpack it.
    prev_next_instruction = None
    text_to_process = input_data

    try:
        state = json.loads(input_data)
        text_to_process       = state.get("text_to_process", input_data)
        prev_next_instruction = state.get("next_instruction")  # from reflect
    except (json.JSONDecodeError, TypeError):
        # Plain text — treat as raw input
        text_to_process = input_data

    lower = text_to_process.lower()

    # Infer target tone from keywords in the input
    tone_keywords = {
        "formal":       ["formal", "official", "corporate"],
        "academic":     ["academic", "scholarly", "research"],
        "casual":       ["casual", "informal", "friendly"],
        "professional": ["professional", "business", "work"],
    }
    target_tone = "professional"  # sensible default
    for tone, keywords in tone_keywords.items():
        if any(kw in lower for kw in keywords):
            target_tone = tone
            break

    # Build constraints — include reflect's next_instruction if present
    constraints = []
    if prev_next_instruction and prev_next_instruction != "None":
        constraints.append(f"Instruction from last reflection: {prev_next_instruction}")
    if any(w in lower for w in ["short", "brief", "concise"]):
        constraints.append("Keep it brief")
    if "simple" in lower:
        constraints.append("Keep it simple")

    return {
        "intent": "Improve grammar and tone of the provided text",
        "text_to_process": text_to_process,
        "target_tone": target_tone,
        "constraints": constraints
    }


# ==========================================
# REASON  —  LLM decides which tool to call
# ==========================================
def reason(observation: dict, memory: list) -> dict:
    """
    Call the LLM to decide WHICH tool to execute next.
    The LLM outputs only a plan (tool name + parameters).
    It does NOT produce the grammar correction itself.
    Returns a plan dict: chosen_action, parameters, reasoning_trace.
    """
    from agent.tools import tools

    client = get_client()
    prompt = REASON_PROMPT.format(
        observation=json.dumps(observation, indent=2),
        memory=json.dumps(memory, indent=2) if memory else "No past memory.",
        tools_schema=json.dumps(tools, indent=2)
    )

    import yaml
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    model_name = config.get("llm", {}).get("model_name", "gemini-3.1-flash-lite")
    temperature = config.get("llm", {}).get("temperature", 0.1)

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature
        )
    )

    plan = parse_json_response(response.text)

    # --- Normalise plan keys ---
    # The LLM sometimes returns 'thought', 'thinking', 'reasoning', or 'rationale'
    # instead of the required 'reasoning_trace'. Unify them.
    for alt_key in ["thought", "thinking", "reasoning", "rationale"]:
        if alt_key in plan and "reasoning_trace" not in plan:
            plan["reasoning_trace"] = plan.pop(alt_key)
            break

    # Guarantee all required keys exist so downstream code never KeyErrors
    plan.setdefault("reasoning_trace", "No reasoning trace provided by LLM.")
    plan.setdefault("chosen_action", None)
    plan.setdefault("parameters", {})

    return plan


# ==========================================
# ACT  —  Executes the pure Python tool
# ==========================================
def act(plan: dict, tools: dict) -> dict:
    """
    Execute the planned action by calling the appropriate Python tool handler.
    The tool handler is 100% pure Python — no LLM involved.
    Returns the result of the tool execution.
    """
    action = plan.get("chosen_action")
    parameters = plan.get("parameters", {})

    if not action:
        return {"error": "No action specified in the plan."}

    if action not in tools:
        return {"error": f"Tool '{action}' does not exist."}

    try:
        handler = tools[action]
        result = handler(parameters)
        return {"action": action, "result": result}
    except Exception as e:
        return {"error": str(e), "action": action}


# ==========================================
# REFLECT  —  Pure Python quality check
# ==========================================
def reflect(result: dict, observation: dict) -> dict:
    """
    Evaluate whether the goal was met by re-running analyze_text on the
    current text. No LLM call — quality is determined by how many grammar
    and tone issues still remain in the text.
    Returns: is_done flag, quality_score, next_instruction, reflection_note.
    """
    from agent.tools import analyze_text, rewrite_text

    target_tone = observation.get("target_tone", "professional")

    # Determine the current state of the text after the last action
    action_result = result.get("result", {})
    current_text = (
        action_result.get("rewritten_text")          # after a rewrite
        or action_result.get("analysis")             # after an analysis (unchanged text)
        or observation.get("text_to_process", "")    # fallback to original
    )

    # Re-analyze the current text using the pure Python tool
    analysis = analyze_text({
        "text": current_text,
        "target_tone": target_tone
    })

    issue_count = analysis.get("issue_count", 0)
    is_done = (issue_count == 0)

    # Score = 10 minus 2 points per remaining issue, floored at 1
    quality_score = max(1, 10 - issue_count * 2)

    reflection_note = (
        f"Text after last action: '{current_text}'. "
        f"Analysis verdict: {analysis.get('verdict', 'Done')}. "
        f"Remaining issues: {analysis.get('issues', [])}."
    )

    return {
        "is_done": is_done,
        "quality_score": quality_score,
        "next_instruction": (
            "None"
            if is_done
            else f"Rewrite the text to fix: {analysis.get('issues', [])}"
        ),
        "reflection_note": reflection_note,
        "current_text": current_text
    }
