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
    """Convert a college dict to a searchable text string"""
    courses = ", ".join(college.get("courses_offered", []))
    fees_parts = [f"{k}: INR {v}/year" for k, v in college.get("fees", {}).items()]
    fees = "; ".join(fees_parts)
    facilities = ", ".join(college.get("facilities", []))
    exams = ", ".join(college.get("entrance_exam", []))

    return f"""
College: {college['college_name']}
City: {college.get('city', '')}
Type: {college.get('institution_type', '')} — {college.get('institution_subtype', '')}
Ownership: {college.get('ownership', '')}
Courses Offered: {courses}
Fees: {fees}
Ranking: {college.get('ranking', '')}
Placement Rate: {college.get('placement_rate', '')}%
Average Package: INR {college.get('average_package', 0):,}/year
Highest Package: INR {college.get('highest_package', 0):,}/year
Entrance Exams Required: {exams}
Admission Process: {college.get('admission_process', '')}
Facilities: {facilities}
Website: {college.get('website', '')}
Phone: {college.get('phone_number', '')}
Email: {college.get('email', '')}
Admission Open: {college.get('admission_open_date', '')}
Application Deadline: {college.get('application_deadline', '')}
""".strip()


def career_to_text(career: dict) -> str:
    colleges = ", ".join(career.get("uttarakhand_colleges_offering", []))
    exams = ", ".join(career.get("key_entrance_exams", []))
    skills = ", ".join(career.get("skills_required", []))
    roles = ", ".join(career.get("job_roles", []))
    aliases = ", ".join(career.get("also_known_as", []))

    return f"""
Career: {career['career_name']} (also known as: {aliases})
Category: {career.get('category', '')}
Description: {career.get('description', '')}
Stream Required (Class 11-12): {career.get('required_stream_class_11_12', '')}
Path after 10th: {career.get('path_after_10th', '')}
Path after 12th: {career.get('path_after_12th', '')}
Path after Graduation: {career.get('path_after_graduation', '')}
Primary Degree: {career.get('primary_degree', '')} ({career.get('duration_years', '')} years)
Alternative Degrees: {", ".join(career.get("alternative_degrees", []))}
Entrance Exams: {exams}
Average Salary (Entry): INR {career.get('avg_salary_entry_inr', 0):,}/year
Average Salary (Mid): INR {career.get('avg_salary_mid_inr', 0):,}/year
Average Salary (Senior): INR {career.get('avg_salary_senior_inr', 0):,}/year
Uttarakhand Colleges Offering This: {colleges}
Skills Required: {skills}
Job Roles: {roles}
""".strip()


def exam_to_text(exam: dict) -> str:
    colleges = ", ".join(exam.get("uttarakhand_colleges_using", []))
    subjects = ", ".join(exam.get("subjects", [])) if isinstance(exam.get("subjects"), list) else str(exam.get("subjects", ""))

    return f"""
Entrance Exam: {exam['exam_name']} — {exam.get('full_name', '')}
Conducting Body: {exam.get('conducting_body', '')}
For Courses: {", ".join(exam.get('for_courses', []))}
For Colleges: {exam.get('for_colleges', '')}
Frequency: {exam.get('frequency', '')}
Eligibility: {exam.get('eligibility', '')}
Mode: {exam.get('exam_mode', '')}
Total Marks: {exam.get('total_marks', '')}
Duration: {exam.get('duration_hours', '')} hours
Subjects: {subjects}
Official Website: {exam.get('official_website', '')}
Uttarakhand Colleges Using This Exam: {colleges}
Preparation Tips: {exam.get('preparation_tips', '')}
""".strip()


def scholarship_to_text(s: dict) -> str:
    return f"""
Scholarship: {s['name']}
Type: {s.get('type', '')}
Category/Who Can Apply: {s.get('category', '')}
Amount: {s.get('amount', '')}
Eligibility: {s.get('eligibility', '')}
How to Apply: {s.get('apply_at', '')}
Deadline: {s.get('deadline', '')}
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


def ingest_all_data():
    vector_store.create_table_if_not_exists()
    vectors = []

    # Load and ingest colleges
    colleges_path = get_data_path("uttarakhand_colleges_db.json")
    print("Ingesting colleges...")
    with open(colleges_path, "r", encoding="utf-8") as f:
        college_data = json.load(f)

    for college in college_data["colleges"]:
        text = college_to_text(college)
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            embedding = embed_text(chunk)
            safe_id = f"college-{ascii_only_id(college['college_name'], 40)}-{i}"
            vectors.append({
                "id": safe_id,
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "source_type": "college",
                    "college_name": college["college_name"],
                    "city": college.get("city", ""),
                    "institution_type": college.get("institution_type", ""),
                }
            })

    # Load and ingest careers
    careers_path = get_data_path("career_paths.json")
    print("Ingesting career paths...")
    with open(careers_path, "r", encoding="utf-8") as f:
        career_data = json.load(f)

    for career in career_data["careers"]:
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

    # Load and ingest exams
    exams_path = get_data_path("entrance_exams.json")
    print("Ingesting entrance exams...")
    with open(exams_path, "r", encoding="utf-8") as f:
        exam_data = json.load(f)

    for exam in exam_data["exams"]:
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

    # Load and ingest scholarships
    scholarships_path = get_data_path("scholarships.json")
    print("Ingesting scholarships...")
    with open(scholarships_path, "r", encoding="utf-8") as f:
        scholarship_data = json.load(f)

    for s in scholarship_data["scholarships"]:
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
