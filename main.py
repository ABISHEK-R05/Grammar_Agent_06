import json
import time
import uuid
import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

from agent.loop import perceive, reason, act, reflect
from agent.tools import tool_handlers
from agent.memory_manager import save, recall
from agent.harness import AgentHarness, call_with_retry
from agent.logger import log_step

def run_agentic_loop(input_text: str, session_id: str):
    harness = AgentHarness("config.yaml")
    
    print(f"\n--- Starting Agentic Loop for Session: {session_id} ---")
    print(f"Input: {input_text}\n")
    
    is_done = False
    iteration = 1
    last_reflection_output = None
    last_reflection = {}          # stores reflect's output to feed into next perceive

    # Initialize observation
    observation = {"raw_input": input_text, "status": "started"}

    while not is_done and iteration <= harness.max_iterations:
        print(f"\n[Iteration {iteration}]")
        
        # 1. PERCEIVE — pure Python, no LLM
        # On iteration > 1, feed reflect's next_instruction back so perceive
        # can incorporate it as an additional constraint.
        t0 = time.time()
        try:
            perceive_input = json.dumps({
                "text_to_process": observation.get("text_to_process", input_text),
                "next_instruction": last_reflection.get("next_instruction")
            })
            new_observation = perceive(perceive_input)
            observation.update(new_observation)
            harness.check_token_budget(str(observation))
        except Exception as e:
            print(f"Perceive failed: {e}")
        t1 = time.time()
        log_step(iteration, "perceive", "Raw input or past state", json.dumps(observation), (t1-t0)*1000)

        # 2. REASON (with memory recall)
        t0 = time.time()
        memory_context = []
        try:
            # Simple query extraction
            query_str = observation.get("text_to_process", input_text)
            memory_context = recall(session_id, query_str)
        except Exception as e:
            print(f"Memory read warning: {e}. Continuing without memory.")
            
        try:
            plan = call_with_retry(reason, observation, memory_context)
            harness.check_token_budget(str(plan))
        except Exception as e:
            # Fallback for reason: return a safe empty plan
            print(f"Reason failed: {e}")
            plan = {"chosen_action": None, "error": str(e)}
            
        t1 = time.time()
        log_step(iteration, "reason", "Observation + Memory", json.dumps(plan), (t1-t0)*1000)
        
        # 3. ACT
        t0 = time.time()
        # Ensure we always pass the handlers down
        result = act(plan, tool_handlers) 
        harness.check_token_budget(str(result))
        t1 = time.time()
        log_step(iteration, "act", plan.get("chosen_action", "None"), json.dumps(result), (t1-t0)*1000)
        
        # 4. REFLECT (with memory write)
        t0 = time.time()
        try:
            reflection = call_with_retry(reflect, result, observation)
            harness.check_token_budget(str(reflection))
        except Exception as e:
            # Fallback: force stop if reflect completely fails
            print(f"Reflect failed: {e}")
            reflection = {"is_done": True, "error": str(e)}
            
        t1 = time.time()
        log_step(iteration, "reflect", "Result + Observation", json.dumps(reflection), (t1-t0)*1000)
        
        # Memory Write
        if "reflection_note" in reflection:
            save(session_id, reflection["reflection_note"], {"iteration": iteration})

        # Store reflect output so next perceive call can consume next_instruction
        last_reflection = reflection

        # Update state for next loop
        # Pass the progressively improved text forward so next iteration works on latest version
        observation["last_result"] = result
        observation["last_reflection"] = reflection
        if "current_text" in reflection:
            observation["text_to_process"] = reflection["current_text"]
        
        # Guardrails Check
        if last_reflection_output == json.dumps(reflection):
            print("\n[GUARDRAIL] STUCK state detected: Reflection is identical to previous iteration. Breaking loop.")
            is_done = True
            reflection["status"] = "STUCK"
            break
            
        last_reflection_output = json.dumps(reflection)
        is_done = reflection.get("is_done", False)
        iteration += 1

    if not is_done and iteration > harness.max_iterations:
         print(f"\n[GUARDRAIL] Max iterations ({harness.max_iterations}) reached.")
         reflection["status"] = "PARTIAL"

    print("\n--- Agentic Loop Finished ---")
    print(f"Final Status: {reflection.get('status', 'SUCCESS')}")
    print(f"Final Result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    import sys
    
    # Use the provided command line argument as input, or fall back to the sample
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = "Its very crucial that u fix this bug right now, me and my team is waiting."
        print("No input provided. Using default sample text.")
        print("Tip: You can pass your own text! Example: python main.py 'your sentence here'\n")
        
    session_id = str(uuid.uuid4())
    run_agentic_loop(user_input, session_id)
