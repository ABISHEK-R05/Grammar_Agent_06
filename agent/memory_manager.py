import os
import chromadb
from chromadb.config import Settings
import hashlib

# Determine the storage path for the ChromaDB
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".chroma_db")

# Initialize ChromaDB client (Persistent)
client = chromadb.PersistentClient(path=DB_DIR)

import yaml

# Load config
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)
collection_name = config.get("memory", {}).get("collection_name", "grammar_agent_memory")

# We use a single collection for all memories, filtering by session_id in metadata
collection = client.get_or_create_collection(name=collection_name)

def save(session_id: str, content: str, metadata: dict) -> None:
    """
    Save an episodic memory or reflection to the vector store.
    """
    # Create a deterministic ID based on content to avoid exact duplicates
    doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # Enrich metadata with the session ID for filtering
    enriched_metadata = metadata.copy()
    enriched_metadata["session_id"] = session_id
    
    try:
        collection.add(
            documents=[content],
            metadatas=[enriched_metadata],
            ids=[f"{session_id}_{doc_id}"]
        )
    except chromadb.errors.DuplicateIDError:
        # If this exact memory for this session already exists, ignore it
        pass

def recall(session_id: str, query: str, top_k: int = 3) -> list[str]:
    """
    Retrieve relevant past memories using semantic similarity search.
    Filters by session_id to ensure episodic memory isolation.
    """
    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"session_id": session_id}
        )
        
        # results["documents"] is a list of lists, since we sent 1 query_text
        if results and results["documents"] and len(results["documents"][0]) > 0:
            return results["documents"][0]
        return []
    except Exception as e:
        print(f"Memory read warning: {e}. Continuing without memory.")
        return []

def clear(session_id: str) -> None:
    """
    Clear all memory for a given session.
    """
    try:
        collection.delete(
            where={"session_id": session_id}
        )
    except Exception:
        pass
