# Harness Engineering Notes

## Overview
A working agent loop is fragile. LLMs hallucinate JSON, APIs rate limit, and loops can get stuck. The harness ensures the agent degrades gracefully and remains observable.

## Retry Logic
`call_with_retry` implements exponential backoff with jitter.
- **Defends against**: Temporary network issues, API timeouts, and 429 Rate Limit errors from the LLM provider.
- **Jitter**: Jitter (adding a random float to the delay) prevents the "thundering herd" problem where multiple blocked processes retry at the exact same millisecond.

## Fallback Strategies
| Failure Mode | Fallback Strategy |
|--------------|-------------------|
| LLM returns unparseable JSON | The parsing function throws a JSONDecodeError. The `call_with_retry` catches it and retries. If it fails max retries, a safe fallback dict is returned. |
| Tool call fails | `act` traps the exception and returns `{"error": "...", "action": action}`. This feeds an error observation back to the LLM, allowing it to adapt rather than crashing the script. |
| Max iterations reached | The main execution loop checks the iteration count. If it exceeds `max_iterations`, the loop breaks and returns the best partial result with a `PARTIAL` status flag. |
| Memory read failure | `memory_manager.recall` wraps the query in a try/except. If it fails, it logs a warning and returns an empty list, allowing the loop to continue without memory. |

## Guardrails
- **Max Iterations**: Prevents runaway LLM costs.
- **Infinite Loop Detection**: The harness stores the last `reflect` output. If the exact same reflection output occurs twice sequentially, it flags the loop as `STUCK` and exits early.
- **Token Budgeting**: A simple heuristic-based token tracker adds up estimated token usage. If the limit in `config.yaml` is breached, a loud warning is emitted to the logs.

## Observability
The `agent/logger.py` module captures a structured, timestamped JSON log for every step (perceive, reason, act, reflect). This enables post-mortem analysis of *why* the agent failed or *how* it arrived at its final state, which is crucial when operating unsupervised.
