import time
import random
import yaml
import os
from functools import wraps
from google.genai.errors import APIError

def call_with_retry(fn, *args, max_retries=3, base_delay=1.0, **kwargs):
    """
    Exponential backoff with jitter for LLM API calls and tool calls.
    Handles rate limits (429), timeouts, and JSON parsing errors.
    For 429 errors, respects the retryDelay hint from the API response.
    """
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e

            error_str = str(e)

            # Extract retryDelay hint from 429 RESOURCE_EXHAUSTED responses
            suggested_delay = None
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                import re
                match = re.search(r'retryDelay["\s:]+(\d+)', error_str)
                if match:
                    suggested_delay = int(match.group(1)) + random.uniform(0, 2)

            # Use API-suggested delay or fall back to exponential backoff with jitter
            delay = suggested_delay if suggested_delay else (base_delay * (2 ** attempt)) + random.uniform(0, 0.5)
            print(f"Warning: Exception {type(e).__name__} caught. Retrying in {delay:.2f}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(delay)

class AgentHarness:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
            
        self.max_iterations = self.config.get("agent", {}).get("max_iterations", 10)
        self.token_budget = self.config.get("agent", {}).get("token_budget", 100000)
        self.cumulative_tokens = 0
        
    def _estimate_tokens(self, text: str) -> int:
        # Simple heuristic: ~4 chars per token
        return len(str(text)) // 4
        
    def check_token_budget(self, text: str):
        self.cumulative_tokens += self._estimate_tokens(text)
        if self.cumulative_tokens > self.token_budget:
            print(f"WARNING: Token budget exceeded! ({self.cumulative_tokens}/{self.token_budget})")
