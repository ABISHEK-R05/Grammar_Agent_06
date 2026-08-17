# Memory Design Notes

## Chosen Memory Tool: ChromaDB (Vector Store)

To satisfy the requirements of Milestone 2, this agentic loop integrates **ChromaDB** as its memory backend. ChromaDB provides a robust, persistent vector store that enables semantic similarity search over past observations and reflections.

### How Memory is Structured
- **Storage**: Memories are persisted to disk in the `.chroma_db` directory using `chromadb.PersistentClient`.
- **Collection**: All memories are stored in a single collection named `agent_memory`.
- **Isolation**: Episodic boundaries are maintained by injecting the `session_id` into the metadata of every saved memory. Retrievals use ChromaDB's `where` clause to filter strictly by the current `session_id`.
- **Reading**: At the start of the `reason` step, `recall()` uses the current observation text as the query. ChromaDB embeds this query, performs a cosine similarity search against past memories for the session, and returns the top-K matches to provide context to the LLM.
- **Writing**: At the end of the `reflect` step, if the agent learned something new (e.g., a rule to apply next time), it calls `save()` to store the `reflection_note` in the vector database.

### Concrete Example in Action
**Iteration N**:
- *Input*: "Its very crucial too understand this."
- *Agent Reflection*: The agent fixes "too" to "to" and "Its" to "It is". In its `reflection_note`, it states: "For this text, prefer 'critical' over 'very crucial' to sound more professional." This note is saved to ChromaDB.

**Iteration N+1 (Next Loop Iteration / Follow-up Input)**:
- *Input*: "Its very crucial that we act."
- *Memory Recall*: Before reasoning, the agent searches ChromaDB with the new input. The semantic search retrieves the note from Iteration N because of the high contextual similarity around "very crucial".
- *Result*: The agent reads the retrieved memory and immediately replaces "very crucial" with "critical", successfully applying what it learned in the previous step.
