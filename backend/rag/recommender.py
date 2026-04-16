"""
Career Recommendation Engine.
Matches careers from PostgreSQL based on user profile (class, stream, interests).
Returns formatted recommendations to inject into the LLM context.
"""
import json
import logging
from rag.vector_store import get_conn

logger = logging.getLogger("rag.recommender")

# Stream → career category mapping
_STREAM_CAREER_MAP = {
    "pcm": ["Engineering & Technology", "Aviation & Aerospace", "Science & Investigation"],
    "pcb": ["Medical & Healthcare"],
    "commerce": ["Management & Business", "Government & Banking"],
    "arts": ["Media & Entertainment", "Design & Creative Arts", "Law & Legal"],
    "humanities": ["Media & Entertainment", "Design & Creative Arts", "Law & Legal"],
    "science": ["Engineering & Technology", "Medical & Healthcare", "Science & Investigation"],
    # Early interest signals from Class 8-9 onboarding
    "science interests me": ["Engineering & Technology", "Medical & Healthcare", "Science & Investigation"],
    "commerce interests me": ["Management & Business", "Government & Banking"],
    "arts interests me": ["Media & Entertainment", "Design & Creative Arts", "Law & Legal"],
}

# Class level → which path column to highlight
_CLASS_PATH_COL = {
    "8th": "path_after_8th",
    "9th": "path_after_8th",
    "10th": "path_after_10th",
    "12th": "path_after_12th",
    "graduate": "path_after_graduation",
    "working professional": "path_after_graduation",
}


def get_career_recommendations(
    current_class: str = None,
    stream: str = None,
    career_interest: str = None,
    budget_per_year: int = None,
    limit: int = 5,
) -> dict:
    """
    Query careers table and return personalized recommendations.

    Returns: {
        "recommendations": list of career dicts,
        "context_text": str (formatted for LLM injection),
        "match_reason": str
    }
    """
    if not current_class and not stream and not career_interest:
        return {"recommendations": [], "context_text": "", "match_reason": ""}

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Build dynamic query based on available profile info
            conditions = []
            params = []

            # Match by stream → category
            stream_lower = (stream or "").lower().strip()
            matched_categories = None
            for key, cats in _STREAM_CAREER_MAP.items():
                if key in stream_lower:
                    matched_categories = cats
                    break

            if matched_categories:
                placeholders = ",".join(["%s"] * len(matched_categories))
                conditions.append(f"category IN ({placeholders})")
                params.extend(matched_categories)

            # If career interest is specified, do a text search
            if career_interest:
                conditions.append(
                    "(career_name ILIKE %s OR description ILIKE %s OR category ILIKE %s)"
                )
                like_pat = f"%{career_interest}%"
                params.extend([like_pat, like_pat, like_pat])

            if conditions:
                where = " OR ".join(conditions)
                query = f"SELECT * FROM careers WHERE {where} ORDER BY career_name LIMIT %s;"
            else:
                # No filters, return top careers by salary
                query = "SELECT * FROM careers ORDER BY avg_salary_mid_inr DESC NULLS LAST LIMIT %s;"

            params.append(limit)
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            careers = [dict(zip(columns, row)) for row in cur.fetchall()]

        if not careers:
            return {"recommendations": [], "context_text": "", "match_reason": ""}

        # Format recommendations for LLM context
        path_col = _CLASS_PATH_COL.get((current_class or "").lower(), "path_after_12th")
        cls_label = current_class or "your level"

        lines = [f"PERSONALIZED CAREER RECOMMENDATIONS (based on {cls_label} student profile):"]
        match_reason = []

        if matched_categories:
            match_reason.append(f"stream: {stream}")
        if career_interest:
            match_reason.append(f"interest: {career_interest}")

        for c in careers:
            name = c.get("career_name", "Unknown")
            category = c.get("category", "")
            entry_salary = c.get("avg_salary_entry_inr")
            mid_salary = c.get("avg_salary_mid_inr")
            path_guidance = c.get(path_col, "") or ""
            degree = c.get("primary_degree", "")

            # Parse JSON fields
            skills = c.get("skills_required", [])
            if isinstance(skills, str):
                try:
                    skills = json.loads(skills)
                except Exception:
                    skills = []

            uk_colleges = c.get("uttarakhand_colleges_offering", [])
            if isinstance(uk_colleges, str):
                try:
                    uk_colleges = json.loads(uk_colleges)
                except Exception:
                    uk_colleges = []

            salary_str = ""
            if entry_salary and mid_salary:
                salary_str = f"INR {entry_salary // 100000}L - {mid_salary // 100000}L LPA"
            elif entry_salary:
                salary_str = f"INR {entry_salary // 100000}L LPA (entry)"

            lines.append(f"\n- {name} ({category})")
            if degree:
                lines.append(f"  Degree: {degree}")
            if salary_str:
                lines.append(f"  Salary Range: {salary_str}")
            if skills:
                lines.append(f"  Key Skills: {', '.join(skills[:5])}")
            if uk_colleges:
                lines.append(f"  Uttarakhand Colleges: {', '.join(uk_colleges[:3])}")
            if path_guidance:
                lines.append(f"  Guidance for {cls_label}: {path_guidance[:200]}")

        context_text = "\n".join(lines)
        reason_str = ", ".join(match_reason) if match_reason else "general"

        return {
            "recommendations": careers,
            "context_text": context_text,
            "match_reason": reason_str,
        }

    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        return {"recommendations": [], "context_text": "", "match_reason": ""}
    finally:
        conn.close()
