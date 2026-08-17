"""
Prompt templates for the agentic loop.

Design note on prompt coverage:
- perceive()  — Pure Python parsing. No LLM prompt needed.
- reason()    — Uses REASON_PROMPT. This is the only LLM call in the loop.
                The LLM's sole job is to decide WHICH tool to call next,
                not to produce the answer itself.
- act()       — Pure Python tool execution. No LLM prompt needed.
- reflect()   — Pure Python quality evaluation using analyze_text.
                No LLM prompt needed.

This design keeps the LLM strictly in the orchestration role and ensures
the grammar correction always comes from the deterministic Python tools.
"""

REASON_PROMPT = """
You are an AI orchestration agent. Your only job is to decide which tool to call next.
You do NOT produce the grammar correction yourself — that is done by the tools.

Study the current observation and any past memory, then select the single best tool to execute.

CURRENT OBSERVATION:
{observation}

PAST MEMORY (from previous sessions):
{memory}

AVAILABLE TOOLS:
{tools_schema}

RULES:
- First call "analyze_text" to identify what is wrong.
- Then call "rewrite_text" to fix the issues found.
- Do NOT hallucinate tools not on the list.
- Do NOT include the corrected text in your response — that is the tool's job.

Your entire response must be a single raw JSON object with NO markdown:
{{
    "reasoning_trace": "Step-by-step explanation of why you chose this tool.",
    "chosen_action": "exact_tool_name",
    "parameters": {{
        "key": "value"
    }}
}}
"""
