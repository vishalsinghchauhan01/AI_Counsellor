"""
College search and listing endpoints.
Reads from PostgreSQL structured tables (primary) with JSON file fallback.
"""
from fastapi import APIRouter, Query
from typing import Optional
from db.schema import get_all_colleges, search_colleges

router = APIRouter()


@router.get("/search")
def search_colleges_endpoint(
    query: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    institution_type: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
    max_fee: Optional[int] = Query(None),
):
    results = search_colleges(
        query=query, city=city,
        institution_type=institution_type,
        course=course, max_fee=max_fee,
    )
    return {"colleges": results, "total": len(results)}


@router.get("/all")
def get_all_colleges_endpoint():
    data = get_all_colleges()
    return {"colleges": data, "total": len(data)}
