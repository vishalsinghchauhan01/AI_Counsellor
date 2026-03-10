import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

_load_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_load_env)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def embed_query(query: str) -> list:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    return response.data[0].embedding


def retrieve_context(query: str, top_k: int = 5, filter_dict: dict = None) -> str:
    """Search PostgreSQL (pgvector) and return relevant context as a string."""
    from rag.vector_store import query as vector_query

    query_embedding = embed_query(query)
    results = vector_query(query_embedding, top_k=top_k, min_score=0.3)

    context_parts = [r["text"] for r in results]
    return "\n\n---\n\n".join(context_parts) if context_parts else "No relevant information found in database."
