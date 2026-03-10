import json
from pathlib import Path
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


def get_college_data():
    base = Path(__file__).resolve().parent.parent.parent  # repo root
    path = base / "data" / "uttarakhand_colleges_db.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["colleges"]


COLLEGE_DATA = get_college_data()


@router.get("/search")
def search_colleges(
    query: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    institution_type: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
    max_fee: Optional[int] = Query(None)
):
    results = list(COLLEGE_DATA)

    if city:
        results = [c for c in results if city.lower() in c.get("city", "").lower()]

    if institution_type:
        results = [c for c in results if institution_type.lower() in c.get("institution_type", "").lower()]

    if course:
        results = [c for c in results if any(
            course.lower() in co.lower() for co in c.get("courses_offered", [])
        )]

    if max_fee:
        results = [c for c in results if any(
            fee <= max_fee for fee in c.get("fees", {}).values()
        )]

    if query:
        query_lower = query.lower()
        results = [c for c in results if
            query_lower in c.get("college_name", "").lower() or
            query_lower in c.get("city", "").lower() or
            any(query_lower in co.lower() for co in c.get("courses_offered", []))
        ]

    return {"colleges": results, "total": len(results)}


@router.get("/all")
def get_all_colleges():
    return {"colleges": COLLEGE_DATA, "total": len(COLLEGE_DATA)}
