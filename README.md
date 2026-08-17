# Agentic Loop - Grammar & Tone Improver

This project implements an agentic loop from scratch in Python to iteratively improve the grammar and tone of text.

It uses the `google-genai` SDK and Gemini 3.1 Flash Lite as the underlying LLM.
No agent frameworks (like LangChain or CrewAI) were used for the core loop, adhering to the challenge rules.

## Setup Instructions

1. Ensure you have Python 3.10+ installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the `.env.example` file to `.env` and add your Gemini API key:
   ```bash
   cp .env.example .env
   # Edit .env to set GEMINI_API_KEY
   ```
   *Note: Alternatively, export it directly:*
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

## Running the Agent

Run the main script to start a demo session:
```bash
python main.py
```

The loop will analyze the sample text, rewrite it, and reflect on the changes until it is satisfied with the result.

## Architecture

- **`agent/loop.py`**: Contains the core cognitive functions (`perceive`, `reason`, `act`, `reflect`).
- **`agent/tools.py`**: Defines tools as JSON schemas and their handlers (`analyze_text`, `rewrite_text`).
- **`agent/memory_manager.py`**: Manages episodic memory using a local ChromaDB instance to recall past reflections.
- **`agent/harness.py` & `agent/logger.py`**: Production-grade scaffolding providing exponential backoff retries, guardrails, and structured JSON logging (`logs.jsonl`).

See `PATTERNS.md`, `MEMORY.md`, and `HARNESS.md` for in-depth design notes for each milestone.
