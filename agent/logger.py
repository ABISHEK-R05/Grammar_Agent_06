import json
import logging
from datetime import datetime
import os

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs.jsonl")

def log_step(iteration: int, step_name: str, input_summary: str, output_summary: str, latency_ms: float, errors: str = None):
    """
    Log each step of every loop iteration in structured JSON to a file.
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "iteration": iteration,
        "step": step_name,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "latency_ms": latency_ms,
        "errors": errors
    }
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
        
    # Also log to stdout for visibility
    status = "SUCCESS" if not errors else "ERROR"
    print(f"[{entry['timestamp']}] Iteration {iteration} | Step: {step_name} | {status} | Latency: {latency_ms:.2f}ms")
    if errors:
         print(f"   -> Errors: {errors}")
