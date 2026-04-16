"""
Conversation persistence — stores chat history in PostgreSQL.
Enables cross-device access and analytics on student queries.
"""
import json
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from rag.vector_store import get_conn

logger = logging.getLogger("routers.conversations")
router = APIRouter()

# ---------------------------------------------------------------------------
#  Table creation
# ---------------------------------------------------------------------------

_CONVERSATIONS_DDL = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    label TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
"""

_MESSAGES_DDL = """
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
"""


def _ensure_tables():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(_CONVERSATIONS_DDL)
            cur.execute(_MESSAGES_DDL)
        conn.commit()
    finally:
        conn.close()


_ensure_tables()


# ---------------------------------------------------------------------------
#  Models
# ---------------------------------------------------------------------------

class MessageIn(BaseModel):
    role: str
    content: str
    sources: Optional[list] = None


class SaveConversationRequest(BaseModel):
    conversation_id: str
    user_id: str
    label: str = ""
    messages: List[MessageIn]


class AppendMessageRequest(BaseModel):
    conversation_id: str
    user_id: str
    message: MessageIn


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------

@router.post("/save")
def save_conversation(req: SaveConversationRequest):
    """Save or replace a full conversation (used when frontend saves to history)."""
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                # Upsert conversation
                cur.execute("""
                    INSERT INTO conversations (id, user_id, label, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        label = EXCLUDED.label,
                        updated_at = NOW();
                """, (req.conversation_id, req.user_id, req.label))

                # Replace messages — delete old then insert new
                cur.execute("DELETE FROM messages WHERE conversation_id = %s;", (req.conversation_id,))

                for msg in req.messages[-30:]:  # Cap at 30 messages
                    cur.execute("""
                        INSERT INTO messages (conversation_id, role, content, sources, created_at)
                        VALUES (%s, %s, %s, %s::jsonb, NOW());
                    """, (
                        req.conversation_id,
                        msg.role,
                        msg.content,
                        json.dumps(msg.sources or []),
                    ))
            conn.commit()
        finally:
            conn.close()
        return {"success": True}
    except Exception as e:
        logger.error(f"Save conversation error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/list/{user_id}")
def list_conversations(user_id: str, limit: int = 10):
    """Get recent conversations for a user."""
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.id, c.label, c.created_at,
                           (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) as message_count
                    FROM conversations c
                    WHERE c.user_id = %s
                    ORDER BY c.updated_at DESC
                    LIMIT %s;
                """, (user_id, limit))
                rows = cur.fetchall()
                return {
                    "conversations": [
                        {
                            "id": r[0],
                            "label": r[1],
                            "created_at": r[2].isoformat() if r[2] else None,
                            "message_count": r[3],
                        }
                        for r in rows
                    ]
                }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"List conversations error: {e}")
        return {"conversations": []}


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str):
    """Load a full conversation with all messages."""
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, user_id, label, created_at FROM conversations WHERE id = %s;",
                    (conversation_id,),
                )
                conv = cur.fetchone()
                if not conv:
                    return {"error": "not found"}

                cur.execute("""
                    SELECT role, content, sources
                    FROM messages
                    WHERE conversation_id = %s
                    ORDER BY id ASC;
                """, (conversation_id,))
                msgs = cur.fetchall()

                return {
                    "id": conv[0],
                    "user_id": conv[1],
                    "label": conv[2],
                    "created_at": conv[3].isoformat() if conv[3] else None,
                    "messages": [
                        {"role": m[0], "content": m[1], "sources": m[2] or []}
                        for m in msgs
                    ],
                }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        return {"error": str(e)}


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete a conversation and its messages."""
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM conversations WHERE id = %s;", (conversation_id,))
            conn.commit()
        finally:
            conn.close()
        return {"success": True}
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        return {"success": False, "error": str(e)}
