# Agentic Patterns Research

This document outlines the five core agentic patterns as required by the challenge specification,
and explains which pattern(s) were applied in this loop and why.

---

## Pattern Explanations

### ReAct (Reason + Act)
ReAct is a pattern that interleaves reasoning traces with external action execution in a tight loop. Instead of reasoning in isolation and then acting, the agent alternates between producing a thought (why it is doing something) and taking a concrete action (calling a tool or API), then observes the result before reasoning again. This grounds the LLM's decision-making in real-world feedback rather than hallucinated outputs, making it far more reliable for multi-step tasks. The pattern was introduced by Yao et al. (2022) and has become the foundation for most practical tool-using agents.

### Reflexion
Reflexion extends the basic ReAct loop by adding an explicit self-evaluation step after each action. Rather than moving forward blindly, the agent scores its own output, generates verbal feedback (a "reflection note"), and stores that feedback in memory. On the next iteration, the stored reflection acts as reinforcement — similar to a trial-and-error learning signal but expressed entirely in natural language. The key insight is that LLMs can improve their own outputs through self-critique without any gradient updates, making Reflexion a powerful pattern for iterative refinement tasks.

### Chain-of-Thought (CoT)
Chain-of-Thought prompting is a technique where the model is instructed (or few-shot prompted) to produce intermediate reasoning steps before arriving at a final answer. Instead of jumping straight to an output, the model writes out its logic step by step ("First I need to identify the error, then fix it, then verify…"). This dramatically improves accuracy on tasks requiring multi-step reasoning, arithmetic, or logical inference. CoT is typically embedded inside a prompt and is the simplest of the five patterns — it improves the quality of a single LLM call rather than orchestrating multiple calls.

### Tree of Thoughts (ToT)
Tree of Thoughts generalises Chain-of-Thought from a linear sequence into a branching tree structure. At each decision point, the agent generates multiple candidate reasoning paths (branches), evaluates their promise, and selects the most likely one to continue — pruning dead ends and backtracking when needed. This gives the agent a search-like capability, making it suitable for tasks where the solution space is large and the correct path is not obvious from the first step. It is significantly more compute-intensive than CoT or ReAct but produces much stronger results on complex planning and puzzle tasks.

### LATS (Language Agent Tree Search)
LATS (Introduced by Zhou et al., 2023) combines the search strategy of Monte Carlo Tree Search (MCTS) with LLM-based reasoning and self-evaluation. The agent builds a tree of possible action sequences, uses the LLM to generate candidate actions at each node, scores them with a value function (also LLM-based), and propagates scores back up the tree to guide future exploration. This makes LATS the most powerful but most expensive of the five patterns — it is designed for tasks where exhaustive search is necessary and where false-start recovery is critical.

---

## Chosen Patterns: ReAct + Reflexion

This loop implements a direct combination of **ReAct** and **Reflexion**.

### ReAct in this loop
The `reason` → `act` cycle is the ReAct pattern applied verbatim. In each iteration, the LLM produces a `reasoning_trace` explaining its decision, then chooses a tool (`analyze_text` or `rewrite_text`). The tool executes and returns an observation (the analysis result or the rewritten text). This observation is fed into the next `reason` call, completing the Reason → Act → Observe cycle that defines ReAct.

### Reflexion in this loop
The `reflect` function is the Reflexion mechanism. After each action, it evaluates the current text quality by re-running `analyze_text` and counting remaining issues. It produces a `quality_score`, an `is_done` flag, and a `next_instruction` (verbal reinforcement). Crucially, this `next_instruction` is fed back into the **next `perceive` call** as an additional constraint, so the agent's understanding of the task is updated by its own self-critique — exactly the verbal reinforcement that defines Reflexion.

### Why this combination fits "Improve grammar and tone iteratively"
Improving text is an inherently iterative, self-correcting task. A single pass rarely catches everything, and the quality of the fix depends on being aware of what was wrong. ReAct ensures the agent grounds its decisions in real tool output (not LLM guesses), while Reflexion ensures that knowledge from each iteration is carried forward to the next. Together they create a loop that progressively refines the text until no grammar or tone issues remain — which is exactly what the use case demands.

### Why CoT, ToT, and LATS were not used
- **CoT** is embedded inside the `reasoning_trace` field of the `reason` prompt, but it is not a separate architectural pattern in this loop — just good prompting practice.
- **ToT** and **LATS** require exploring multiple reasoning branches in parallel. For a deterministic, rule-based grammar correction task, the solution space is small and well-defined. Branching would add overhead with no benefit, since the correct action sequence (analyze → rewrite → check) is always linear.
