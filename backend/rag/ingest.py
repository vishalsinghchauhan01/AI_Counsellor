import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from rag import vector_store

# Load .env from backend folder (so it works when run from repo root or backend/)
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ASCII-only IDs for vector rows
def ascii_only_id(s: str, max_len: int = 100) -> str:
    """Replace non-ASCII and problematic chars for safe IDs."""
    out = "".join(c if ord(c) < 128 and c not in "()" else "_" for c in (s or ""))
    out = out.replace(" ", "_").replace("/", "_").replace("—", "_")
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")[:max_len] or "id"


# Resolve data path: same repo root/data (when run from backend/ or backend/rag/)
def get_data_path(filename):
    base = Path(__file__).resolve().parent.parent.parent  # repo root
    return base / "data" / filename


def embed_text(text: str) -> list:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def college_to_text(college: dict) -> str:
    """Convert a college/university dict to a searchable text string."""
    # Support both old (college_name) and new (university_name) keys
    name = college.get('university_name') or college.get('college_name', 'Unknown')
    abbreviation = college.get('abbreviation', '')
    aliases = ", ".join(college.get("also_known_as", []) or [])
    courses = ", ".join(college.get("courses_offered", []) or [])
    fees_parts = []
    for k, v in (college.get("fees", {}) or {}).items():
        if isinstance(v, dict):
            annual = v.get("annual") or 0
            total = v.get("total") or 0
            years = v.get("duration_years") or 0
            fees_parts.append(f"{k}: INR {annual:,}/year, INR {total:,} total ({years} years)")
        elif v:
            fees_parts.append(f"{k}: INR {v:,}/year")
    fees = "; ".join(fees_parts)
    facilities = ", ".join(college.get("facilities", []) or [])
    exams = ", ".join(college.get("entrance_exams") or college.get("entrance_exam", []) or [])

    avg_pkg = college.get('average_package') or 0
    high_pkg = college.get('highest_package') or 0
    placement = college.get('placement_rate') or 0
    established = college.get('established') or ''
    hostel = "Yes" if college.get('hostel_available') else "No"
    hostel_fee = college.get('hostel_fee_annual')
    hostel_str = f"{hostel}" + (f" (INR {hostel_fee:,}/year)" if hostel_fee else "")

    return f"""
University: {name}
Abbreviation: {abbreviation}
Also Known As: {aliases}
City: {college.get('city') or ''}, District: {college.get('district') or ''}
Type: {college.get('institution_type') or ''} — {college.get('institution_subtype') or ''}
Established: {established}
NIRF Ranking: {college.get('nirf_ranking') or 'Not ranked'}
NAAC Grade: {college.get('naac_grade') or 'Not available'}
Courses Offered: {courses}
Fees: {fees}
Placement Rate: {placement}%
Average Package: INR {avg_pkg:,}/year
Highest Package: INR {high_pkg:,}/year
Entrance Exams Required: {exams}
Hostel Available: {hostel_str}
Facilities: {facilities}
Website: {college.get('website') or ''}
""".strip()


def career_to_text(career: dict) -> str:
    colleges = ", ".join(career.get("uttarakhand_colleges_offering") or [])
    exams = ", ".join(career.get("key_entrance_exams") or [])
    skills = ", ".join(career.get("skills_required") or [])
    roles = ", ".join(career.get("job_roles") or [])
    aliases = ", ".join(career.get("also_known_as") or [])

    entry_sal = career.get('avg_salary_entry_inr') or 0
    mid_sal = career.get('avg_salary_mid_inr') or 0
    senior_sal = career.get('avg_salary_senior_inr') or 0

    return f"""
Career: {career.get('career_name', 'Unknown')} (also known as: {aliases})
Category: {career.get('category') or ''}
Description: {career.get('description') or ''}
Stream Required (Class 11-12): {career.get('required_stream_class_11_12') or ''}
Path after 10th: {career.get('path_after_10th') or ''}
Path after 12th: {career.get('path_after_12th') or ''}
Path after Graduation: {career.get('path_after_graduation') or ''}
Primary Degree: {career.get('primary_degree') or ''} ({career.get('duration_years') or ''} years)
Alternative Degrees: {", ".join(career.get("alternative_degrees") or [])}
Entrance Exams: {exams}
Average Salary (Entry): INR {entry_sal:,}/year
Average Salary (Mid): INR {mid_sal:,}/year
Average Salary (Senior): INR {senior_sal:,}/year
Uttarakhand Colleges Offering This: {colleges}
Skills Required: {skills}
Job Roles: {roles}
""".strip()


def exam_to_text(exam: dict) -> str:
    colleges = ", ".join(exam.get("uttarakhand_colleges_using") or [])
    subjects_raw = exam.get("subjects")
    subjects = ", ".join(subjects_raw) if isinstance(subjects_raw, list) else str(subjects_raw or "")

    return f"""
Entrance Exam: {exam.get('exam_name', 'Unknown')} — {exam.get('full_name') or ''}
Conducting Body: {exam.get('conducting_body') or ''}
For Courses: {", ".join(exam.get('for_courses') or [])}
For Colleges: {exam.get('for_colleges') or ''}
Frequency: {exam.get('frequency') or ''}
Eligibility: {exam.get('eligibility') or ''}
Mode: {exam.get('exam_mode') or ''}
Total Marks: {exam.get('total_marks') or ''}
Duration: {exam.get('duration_hours') or ''} hours
Subjects: {subjects}
Official Website: {exam.get('official_website') or ''}
Uttarakhand Colleges Using This Exam: {colleges}
Preparation Tips: {exam.get('preparation_tips') or ''}
""".strip()


def scholarship_to_text(s: dict) -> str:
    return f"""
Scholarship: {s.get('name', 'Unknown')}
Type: {s.get('type') or ''}
Category/Who Can Apply: {s.get('category') or ''}
Amount: {s.get('amount') or ''}
Eligibility: {s.get('eligibility') or ''}
How to Apply: {s.get('apply_at') or ''}
Deadline: {s.get('deadline') or ''}
""".strip()


def chunk_text(text: str, max_chars: int = 1500) -> list:
    """Split long text into chunks with overlap"""
    words = text.split()
    chunks = []
    current = []
    current_len = 0

    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= max_chars:
            chunks.append(" ".join(current))
            overlap = current[-30:]  # keep last 30 words for overlap
            current = overlap
            current_len = sum(len(w) + 1 for w in current)

    if current:
        chunks.append(" ".join(current))
    return chunks


def _load_data_from_db():
    """Load all data from PostgreSQL structured tables."""
    from db.schema import get_all_colleges, get_all_careers, get_all_exams, get_all_scholarships, is_table_empty
    if not is_table_empty("colleges"):
        return {
            "colleges": get_all_colleges(),
            "careers": get_all_careers(),
            "exams": get_all_exams(),
            "scholarships": get_all_scholarships(),
        }
    return None


def _load_data_from_json():
    """Fallback: load data from JSON files."""
    data = {"colleges": [], "careers": [], "exams": [], "scholarships": []}

    # Universities (new curated dataset) — fall back to old colleges_db
    uni_path = get_data_path("uttarakhand_universities.json")
    old_path = get_data_path("uttarakhand_colleges_db.json")
    try:
        if uni_path.exists():
            with open(uni_path, "r", encoding="utf-8") as f:
                data["colleges"] = json.load(f).get("universities", [])
        elif old_path.exists():
            with open(old_path, "r", encoding="utf-8") as f:
                data["colleges"] = json.load(f).get("colleges", [])
    except Exception:
        pass

    other_files = {
        "careers": ("career_paths.json", "careers"),
        "exams": ("entrance_exams.json", "exams"),
        "scholarships": ("scholarships.json", "scholarships"),
    }
    for key, (fname, json_key) in other_files.items():
        path = get_data_path(fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data[key] = json.load(f).get(json_key, [])
        except Exception:
            pass
    return data


def ingest_all_data():
    vector_store.create_table_if_not_exists()
    vector_store.clear_all()  # Clear old vectors for clean re-ingestion
    vectors = []

    # Try PostgreSQL first, fall back to JSON
    print("Loading data for ingestion...")
    try:
        db_data = _load_data_from_db()
    except Exception:
        db_data = None

    if db_data:
        print("  → Reading from PostgreSQL tables")
        all_colleges = db_data["colleges"]
        all_careers = db_data["careers"]
        all_exams = db_data["exams"]
        all_scholarships = db_data["scholarships"]
    else:
        print("  → Reading from JSON files (DB empty or unavailable)")
        json_data = _load_data_from_json()
        all_colleges = json_data["colleges"]
        all_careers = json_data["careers"]
        all_exams = json_data["exams"]
        all_scholarships = json_data["scholarships"]

    # Ingest universities/colleges
    print(f"Ingesting {len(all_colleges)} universities...")
    for college in all_colleges:
        name = college.get("university_name") or college.get("college_name", "Unknown")
        text = college_to_text(college)
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            embedding = embed_text(chunk)
            safe_id = f"college-{ascii_only_id(name, 40)}-{i}"
            vectors.append({
                "id": safe_id,
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "source_type": "college",
                    "college_name": name,
                    "city": college.get("city", ""),
                    "institution_type": college.get("institution_type", ""),
                }
            })

    # Ingest careers
    print(f"Ingesting {len(all_careers)} careers...")
    for career in all_careers:
        text = career_to_text(career)
        embedding = embed_text(text)
        safe_id = f"career-{ascii_only_id(career['career_name'], 60)}"
        vectors.append({
            "id": safe_id,
            "values": embedding,
            "metadata": {
                "text": text,
                "source_type": "career",
                "career_name": career["career_name"],
                "category": career.get("category", ""),
            }
        })

    # Ingest exams
    print(f"Ingesting {len(all_exams)} exams...")
    for exam in all_exams:
        text = exam_to_text(exam)
        embedding = embed_text(text)
        safe_id = f"exam-{ascii_only_id(exam['exam_name'], 50)}"
        vectors.append({
            "id": safe_id,
            "values": embedding,
            "metadata": {
                "text": text,
                "source_type": "exam",
                "exam_name": exam["exam_name"],
            }
        })

    # Ingest scholarships
    print(f"Ingesting {len(all_scholarships)} scholarships...")
    for s in all_scholarships:
        text = scholarship_to_text(s)
        embedding = embed_text(text)
        safe_name = ascii_only_id(s["name"], 50)
        vectors.append({
            "id": f"scholarship-{safe_name}",
            "values": embedding,
            "metadata": {
                "text": text,
                "source_type": "scholarship",
                "scholarship_name": s["name"],
            }
        })

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        vector_store.upsert_batch(batch)
        print(f"Upserted batch {i//batch_size + 1} ({len(batch)} vectors)")

    vector_store.ensure_index()
    print(f"\n✅ Ingestion complete! Total vectors: {len(vectors)}")


if __name__ == "__main__":
    ingest_all_data()
