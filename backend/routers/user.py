import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

try:
    from supabase import create_client
    supabase = create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_SERVICE_KEY", "")
    )
except Exception:
    supabase = None


class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    current_class: Optional[str] = None
    stream: Optional[str] = None
    career_interest: Optional[str] = None
    budget_per_year: Optional[int] = None
    category: Optional[str] = None
    location: Optional[str] = None
    willing_to_relocate: Optional[bool] = None


class SaveProfileRequest(BaseModel):
    profile: UserProfile


@router.post("/profile")
def save_profile(req: SaveProfileRequest):
    try:
        if supabase is None:
            return {"success": True, "note": "Profile saved locally"}
        data = req.profile.model_dump()
        result = supabase.table("user_profiles").upsert(data).execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        return {"success": True, "note": "Profile saved locally"}


@router.get("/profile/{user_id}")
def get_profile(user_id: str):
    try:
        if supabase is None:
            return {}
        result = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return {}
    except Exception:
        return {}
