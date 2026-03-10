"""
PostgreSQL + pgvector for local vector storage.
Requires: PostgreSQL with pgvector extension, DATABASE_URL in .env.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

_load_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_load_env)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/uttarapath")
TABLE_NAME = "uttarapath_vectors"
VECTOR_DIM = 1536


def get_conn():
    """Get a database connection with pgvector registered."""
    import psycopg2
    from pgvector.psycopg2 import register_vector

    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def create_table_if_not_exists():
    """Create the vectors table and enable pgvector extension."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id TEXT PRIMARY KEY,
                    embedding vector({VECTOR_DIM}),
                    content TEXT NOT NULL,
                    source_type TEXT,
                    metadata JSONB
                );
            """)
        conn.commit()
        print(f"Table {TABLE_NAME} ready.")
    finally:
        conn.close()


def ensure_index():
    """Create IVFFlat index for faster search if table has enough rows."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
            if cur.fetchone()[0] < 50:
                return
            cur.execute(
                "SELECT 1 FROM pg_indexes WHERE tablename = %s AND indexname = %s;",
                (TABLE_NAME, f"{TABLE_NAME}_embedding_idx"),
            )
            if cur.fetchone() is not None:
                return
            try:
                cur.execute(f"""
                    CREATE INDEX {TABLE_NAME}_embedding_idx
                    ON {TABLE_NAME}
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                conn.commit()
                print("Index created for faster search.")
            except Exception:
                conn.rollback()
    finally:
        conn.close()


def upsert_batch(vectors):
    """
    Insert or replace a batch of vectors.
    Each item: {"id": str, "values": list[float], "metadata": dict}
    metadata must contain "text" (stored as content) and optionally "source_type", etc.
    """
    if not vectors:
        return
    import psycopg2
    from pgvector.psycopg2 import register_vector

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for v in vectors:
                vid = v["id"]
                emb = v["values"]
                meta = v.get("metadata", {})
                content = meta.get("text", "")
                source_type = meta.get("source_type", "")
                # Store full metadata as JSONB (without huge text if duplicated)
                meta_json = json.dumps({k: v for k, v in meta.items() if k != "text"})
                cur.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (id, embedding, content, source_type, metadata)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        content = EXCLUDED.content,
                        source_type = EXCLUDED.source_type,
                        metadata = EXCLUDED.metadata;
                    """,
                    (vid, emb, content, source_type, meta_json),
                )
        conn.commit()
    finally:
        conn.close()


def query(query_embedding: list, top_k: int = 5, min_score: float = 0.3):
    """
    Cosine similarity search. Returns list of dicts with "text" and "score".
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # <=> is cosine distance (0 = same, 2 = opposite). similarity = 1 - distance
            cur.execute(
                f"""
                SELECT content, 1 - (embedding <=> %s::vector) AS score
                FROM {TABLE_NAME}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (query_embedding, query_embedding, top_k),
            )
            rows = cur.fetchall()
        return [{"text": r[0], "score": float(r[1])} for r in rows if r[1] and float(r[1]) >= min_score]
    finally:
        conn.close()
