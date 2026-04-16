import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

_load_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_load_env)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger("rag.retriever")

_REWRITE_SYSTEM = (
    "You are a query rewriter for a career-counselling RAG system. "
    "Given the conversation history and the student's latest message, "
    "rewrite ONLY the latest message into a single standalone search query "
    "that resolves all pronouns, references ('this', 'that', 'it', 'these'), "
    "and ellipsis so the query makes sense without any prior context. "
    "Output ONLY the rewritten query — no explanation, no quotes."
)


def rewrite_query(message: str, history: list[dict]) -> str:
    """Use a fast LLM call to resolve references in the user's message.

    Turns vague follow-ups like 'which colleges offer this?' into
    standalone queries like 'which colleges in Uttarakhand offer nursing courses?'
    by reading the conversation history.

    Falls back to the original message if rewriting fails or history is empty.
    """
    if not history:
        return message

    # Build a compact history string (last 10 messages, assistant replies capped)
    turns = []
    for msg in history[-10:]:
        role = "Student" if msg.get("role") == "user" else "Counsellor"
        content = msg.get("content", "")
        if role == "Counsellor":
            content = content[:500]
        turns.append(f"{role}: {content}")
    turns.append(f"Student: {message}")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _REWRITE_SYSTEM},
                {"role": "user", "content": "\n".join(turns)},
            ],
            max_tokens=150,
            temperature=0,
        )
        rewritten = response.choices[0].message.content.strip()
        if rewritten:
            logger.info("Query rewritten: '%s' -> '%s'", message, rewritten)
            return rewritten
    except Exception as e:
        logger.warning("Query rewrite failed, using original: %s", e)

    return message


def embed_query(query: str) -> list:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    return response.data[0].embedding


def _fetch_colleges_by_course(query: str) -> list[dict]:
    """Do a structured DB search for colleges matching course keywords in the query.

    This complements vector search by finding universities that offer a course
    even if their vector text chunk didn't score high enough (e.g., IIT Roorkee
    offers M.Sc but user searched "BSc Physics" — vector misses it, but a
    broader keyword match on the courses_offered JSONB array catches it).
    """
    from rag.vector_store import get_conn

    # Extract likely course/subject keywords from the query
    query_lower = query.lower()

    # Common course keywords that signal a college-listing query
    course_signals = [
        "college", "university", "universities", "colleges", "admission",
        "best", "top", "list", "bsc", "b.sc", "btech", "b.tech", "mba",
        "mca", "bba", "bca", "mbbs", "md", "msc", "m.sc", "bpharm",
        "b.pharm", "mtech", "m.tech", "bed", "b.ed", "llb", "ba",
        "bcom", "b.com", "bdes", "b.des", "barch", "b.arch", "phd",
        "nursing", "engineering", "medical", "pharmacy", "law",
        "management", "science", "arts", "commerce", "physics",
        "chemistry", "biology", "mathematics", "computer", "agriculture",
        "forestry", "hotel management", "bhm", "paramedical",
    ]

    is_college_query = any(kw in query_lower for kw in course_signals)
    if not is_college_query:
        return []

    # Build search terms from the query to match against courses_offered
    # e.g., "BSc Physics" -> search for "B.Sc" and "Physics"
    search_terms = []

    # Map common abbreviations to their DB forms
    abbrev_map = {
        "bsc": "B.Sc", "b.sc": "B.Sc", "btech": "B.Tech", "b.tech": "B.Tech",
        "mba": "MBA", "mca": "MCA", "bba": "BBA", "bca": "BCA",
        "mbbs": "MBBS", "msc": "M.Sc", "m.sc": "M.Sc", "mtech": "M.Tech",
        "m.tech": "M.Tech", "bpharm": "B.Pharm", "b.pharm": "B.Pharm",
        "mpharm": "M.Pharm", "m.pharm": "M.Pharm", "bed": "B.Ed",
        "b.ed": "B.Ed", "llb": "LLB", "llm": "LLM", "bcom": "B.Com",
        "b.com": "B.Com", "bdes": "B.Des", "b.des": "B.Des",
        "barch": "B.Arch", "b.arch": "B.Arch", "phd": "PhD",
        "bhm": "BHM", "ba": "BA", "md": "MD", "ms": "MS",
    }

    words = query_lower.split()
    for word in words:
        clean = word.strip(".,?!:;")
        if clean in abbrev_map:
            search_terms.append(abbrev_map[clean])

    # Also add subject keywords
    subject_keywords = [
        "engineering", "medical", "pharmacy", "law", "management", "nursing",
        "science", "arts", "commerce", "physics", "chemistry", "biology",
        "computer", "agriculture", "forestry", "hotel", "paramedical",
        "architecture", "design", "education",
    ]
    for kw in subject_keywords:
        if kw in query_lower:
            search_terms.append(kw)

    if not search_terms:
        # Broad college query without specific course — return all colleges
        # so the LLM can recommend based on its ranking knowledge
        search_terms = ["%"]

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Search colleges where any course matches any of our search terms
            # OR just get all colleges for broad queries
            if search_terms == ["%"]:
                cur.execute("""
                    SELECT college_name, abbreviation, courses_offered, fees,
                           nirf_ranking, naac_grade, institution_type, city,
                           placement_rate, average_package, hostel_available,
                           hostel_fee_annual, website
                    FROM colleges ORDER BY college_name LIMIT 20;
                """)
            else:
                # Build OR conditions for each search term
                conditions = []
                params = []
                for term in search_terms:
                    conditions.append(
                        "EXISTS (SELECT 1 FROM jsonb_array_elements_text(courses_offered) AS elem WHERE elem ILIKE %s)"
                    )
                    params.append(f"%{term}%")
                    # Also match college name and abbreviation
                    conditions.append("college_name ILIKE %s")
                    params.append(f"%{term}%")
                    conditions.append("abbreviation ILIKE %s")
                    params.append(f"%{term}%")

                where = " OR ".join(conditions)
                cur.execute(f"""
                    SELECT college_name, abbreviation, courses_offered, fees,
                           nirf_ranking, naac_grade, institution_type, city,
                           placement_rate, average_package, hostel_available,
                           hostel_fee_annual, website
                    FROM colleges WHERE {where} ORDER BY college_name;
                """, params)

            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        logger.warning("Structured college search failed: %s", e)
        return []
    finally:
        conn.close()


def _college_row_to_context(c: dict) -> str:
    """Convert a structured DB college row to a compact context string."""
    name = c.get("college_name", "")
    abbr = c.get("abbreviation", "")
    courses = c.get("courses_offered", []) or []
    if isinstance(courses, str):
        import json
        courses = json.loads(courses)
    courses_str = ", ".join(courses) if courses else ""

    fees = c.get("fees", {}) or {}
    if isinstance(fees, str):
        import json
        fees = json.loads(fees)
    fees_parts = []
    for k, v in fees.items():
        if isinstance(v, dict):
            annual = v.get("annual") or 0
            total = v.get("total") or 0
            years = v.get("duration_years") or 0
            fees_parts.append(f"{k}: INR {annual:,}/year, INR {total:,} total ({years} yrs)")
        elif v:
            fees_parts.append(f"{k}: INR {v:,}/year")
    fees_str = "; ".join(fees_parts)

    nirf = c.get("nirf_ranking") or "Not ranked"
    naac = c.get("naac_grade") or "N/A"
    inst_type = c.get("institution_type") or ""
    city = c.get("city") or ""
    placement = c.get("placement_rate") or 0
    avg_pkg = c.get("average_package") or 0
    hostel = "Yes" if c.get("hostel_available") else "No"
    hostel_fee = c.get("hostel_fee_annual")
    hostel_str = hostel + (f" (INR {hostel_fee:,}/yr)" if hostel_fee else "")
    website = c.get("website") or ""

    return (
        f"University: {name} ({abbr}) | {inst_type} | {city}\n"
        f"NIRF: {nirf} | NAAC: {naac}\n"
        f"Courses: {courses_str}\n"
        f"Fees: {fees_str}\n"
        f"Placement: {placement}% | Avg Package: INR {avg_pkg:,}/yr\n"
        f"Hostel: {hostel_str} | Website: {website}"
    )


def retrieve_context(query: str, top_k: int = 10, filter_dict: dict = None) -> dict:
    """Hybrid search: vector similarity + structured DB query for colleges.

    Returns:
        {
            "context": str,          # text to inject into the LLM prompt
            "college_names": [str],   # colleges found in results
        }
    """
    from rag.vector_store import query as vector_query, query_with_metadata

    query_embedding = embed_query(query)
    results = query_with_metadata(query_embedding, top_k=top_k, min_score=0.3)

    context_parts = []
    college_names = []
    seen_colleges = set()

    for r in results:
        context_parts.append(r["text"])
        meta = r.get("metadata") or {}
        if r.get("source_type") == "college" and meta.get("college_name"):
            cname = meta["college_name"]
            college_names.append(cname)
            seen_colleges.add(cname.lower())

    # --- Hybrid: structured DB search for colleges ---
    db_colleges = _fetch_colleges_by_course(query)
    db_context_parts = []
    for c in db_colleges:
        cname = c.get("college_name", "")
        if cname.lower() not in seen_colleges:
            db_context_parts.append(_college_row_to_context(c))
            college_names.append(cname)
            seen_colleges.add(cname.lower())

    # Add structured results under a clear heading so the LLM knows these are from the DB
    if db_context_parts:
        structured_block = (
            "--- ADDITIONAL UNIVERSITIES FROM DATABASE (may also offer relevant courses) ---\n\n"
            + "\n\n---\n\n".join(db_context_parts)
        )
        context_parts.append(structured_block)

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant information found in database."
    return {
        "context": context,
        "college_names": college_names,
    }
