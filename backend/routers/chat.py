import os
import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI
from slowapi import Limiter
from slowapi.util import get_remote_address
from rag.retriever import retrieve_context, rewrite_query
from rag.prompts import SYSTEM_PROMPT, ONBOARDING_PROMPT

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
limiter = Limiter(key_func=get_remote_address)


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str = Field(..., max_length=5000)


class UserProfile(BaseModel):
    current_class: Optional[str] = None
    stream: Optional[str] = None
    career_interest: Optional[str] = None
    budget_per_year: Optional[int] = None
    category: Optional[str] = None
    location_preference: Optional[str] = None
    willing_to_relocate: Optional[bool] = None


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    history: List[Message] = Field(default=[], max_length=50)
    user_profile: Optional[UserProfile] = None
    session_id: Optional[str] = None


class OnboardingRequest(BaseModel):
    session_id: Optional[str] = None


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    try:
        # Rewrite vague follow-ups into standalone queries using
        # conversation history so the vector search finds the right context.
        # e.g. "which colleges offer this?" → "which Uttarakhand colleges offer nursing courses?"
        history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
        rag_query = rewrite_query(req.message, history_dicts)

        # Retrieve relevant context from database (PostgreSQL/pgvector)
        retrieval = retrieve_context(rag_query, top_k=10)
        context = retrieval["context"]
        college_names = retrieval["college_names"]

        # Build user profile string
        profile_str = "Not collected yet."
        if req.user_profile:
            profile_parts = []
            if req.user_profile.current_class:
                profile_parts.append(f"Current Class: {req.user_profile.current_class}")
            if req.user_profile.stream:
                profile_parts.append(f"Stream: {req.user_profile.stream}")
            if req.user_profile.career_interest:
                profile_parts.append(f"Career Interest: {req.user_profile.career_interest}")
            if req.user_profile.budget_per_year:
                profile_parts.append(f"Annual Budget: INR {req.user_profile.budget_per_year:,}")
            if req.user_profile.category:
                profile_parts.append(f"Category: {req.user_profile.category}")
            if req.user_profile.location_preference:
                profile_parts.append(f"Location Preference: {req.user_profile.location_preference}")
            if req.user_profile.willing_to_relocate is not None:
                profile_parts.append(f"Willing to Relocate: {'Yes' if req.user_profile.willing_to_relocate else 'No'}")
            profile_str = "\n".join(profile_parts) if profile_parts else "Not collected yet."

        # Build chat history string
        history_str = ""
        for msg in req.history[-8:]:  # last 8 messages for context window
            role = "Student" if msg.role == "user" else "AI Counsellor"
            history_str += f"{role}: {msg.content}\n\n"

        # Build the final system prompt
        system = SYSTEM_PROMPT.format(
            user_profile=profile_str,
            context=context,
            chat_history=history_str or "This is the start of the conversation."
        )

        # Build messages for GPT
        messages = [{"role": "system", "content": system}]
        for msg in req.history[-6:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": req.message})

        # Stream response
        def generate():
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1500,
                temperature=0.4,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
            # Send retrieved college names so the frontend can show cards
            # without hardcoded name lists or fetching all colleges
            if college_names:
                yield f"data: {json.dumps({'sources': {'colleges': college_names}})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/onboarding")
@limiter.limit("10/minute")
async def get_onboarding_message(request: Request, req: OnboardingRequest):
    """Get the initial greeting message"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ONBOARDING_PROMPT},
                {"role": "user", "content": "Hello, I just opened the app."}
            ],
            max_tokens=300,
            temperature=0.8
        )
        return {"message": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
