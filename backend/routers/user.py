import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from db.schema import upsert_user_profile, get_user_profile

router = APIRouter()
logger = logging.getLogger("routers.user")


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
        data = req.profile.model_dump()
        result = upsert_user_profile(data)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Failed to save user profile: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save profile")


@router.get("/profile/{user_id}")
def get_profile(user_id: str):
    try:
        profile = get_user_profile(user_id)
        if profile is None:
            return {}
        return profile
    except Exception as e:
        logger.error("Failed to get user profile: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve profile")
