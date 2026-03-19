"""
PostgreSQL structured data tables for colleges, careers, exams, scholarships.
Uses raw psycopg2 (same as vector_store.py) — no ORM needed.
Tables mirror the Pydantic schemas in scraper/schemas.py.
"""
import json
import logging
from pathlib import Path

from rag.vector_store import get_conn

logger = logging.getLogger("db.schema")

# ---------------------------------------------------------------------------
#  Table creation
# ---------------------------------------------------------------------------

_ENABLE_PGCRYPTO = "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

_COLLEGES_DDL = """
CREATE TABLE IF NOT EXISTS colleges (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    college_name TEXT UNIQUE NOT NULL,
    city TEXT DEFAULT '',
    institution_type TEXT DEFAULT '',
    institution_subtype TEXT DEFAULT '',
    ownership TEXT DEFAULT '',
    courses_offered JSONB DEFAULT '[]',
    fees JSONB DEFAULT '{}',
    eligibility JSONB DEFAULT '{}',
    admission_process TEXT DEFAULT '',
    entrance_exam JSONB DEFAULT '[]',
    placement_rate INTEGER CHECK (placement_rate IS NULL OR (placement_rate >= 0 AND placement_rate <= 100)),
    average_package BIGINT,
    highest_package BIGINT,
    ranking TEXT DEFAULT '',
    facilities JSONB DEFAULT '[]',
    website TEXT DEFAULT '',
    phone_number TEXT DEFAULT '',
    email TEXT DEFAULT '',
    admission_open_date TEXT DEFAULT '',
    application_deadline TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

_CAREERS_DDL = """
CREATE TABLE IF NOT EXISTS careers (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    career_name TEXT UNIQUE NOT NULL,
    also_known_as JSONB DEFAULT '[]',
    category TEXT DEFAULT '',
    description TEXT DEFAULT '',
    required_stream_class_11_12 TEXT DEFAULT '',
    path_after_10th TEXT DEFAULT '',
    path_after_12th TEXT DEFAULT '',
    path_after_graduation TEXT DEFAULT '',
    key_entrance_exams JSONB DEFAULT '[]',
    primary_degree TEXT DEFAULT '',
    alternative_degrees JSONB DEFAULT '[]',
    duration_years INTEGER,
    avg_salary_entry_inr BIGINT,
    avg_salary_mid_inr BIGINT,
    avg_salary_senior_inr BIGINT,
    top_companies JSONB DEFAULT '[]',
    uttarakhand_colleges_offering JSONB DEFAULT '[]',
    skills_required JSONB DEFAULT '[]',
    job_roles JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

_EXAMS_DDL = """
CREATE TABLE IF NOT EXISTS exams (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    exam_name TEXT UNIQUE NOT NULL,
    full_name TEXT DEFAULT '',
    conducting_body TEXT DEFAULT '',
    for_courses JSONB DEFAULT '[]',
    for_colleges TEXT DEFAULT '',
    frequency TEXT DEFAULT '',
    eligibility TEXT DEFAULT '',
    exam_mode TEXT DEFAULT '',
    total_marks INTEGER,
    duration_hours FLOAT,
    subjects JSONB DEFAULT '[]',
    official_website TEXT DEFAULT '',
    uttarakhand_colleges_using JSONB DEFAULT '[]',
    preparation_tips TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

_SCHOLARSHIPS_DDL = """
CREATE TABLE IF NOT EXISTS scholarships (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL,
    type TEXT DEFAULT '',
    category TEXT DEFAULT '',
    amount TEXT DEFAULT '',
    eligibility TEXT DEFAULT '',
    apply_at TEXT DEFAULT '',
    deadline TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""


def init_tables():
    """Create all structured data tables if they don't exist."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(_ENABLE_PGCRYPTO)
            cur.execute(_COLLEGES_DDL)
            cur.execute(_CAREERS_DDL)
            cur.execute(_EXAMS_DDL)
            cur.execute(_SCHOLARSHIPS_DDL)
        conn.commit()
        logger.info("Structured data tables ready.")
    finally:
        conn.close()


def is_table_empty(table_name: str) -> bool:
    """Check if a table has zero rows."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name};")
            return cur.fetchone()[0] == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
#  UPSERT helpers
# ---------------------------------------------------------------------------

def _json_col(val) -> str:
    """Serialize a Python object to JSON string for JSONB columns."""
    if val is None:
        return "[]"
    return json.dumps(val, ensure_ascii=False, default=str)


def upsert_colleges_batch(colleges: list[dict]):
    """Batch upsert colleges. Uses ON CONFLICT to update existing rows."""
    if not colleges:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for c in colleges:
                cur.execute("""
                    INSERT INTO colleges (
                        college_name, city, institution_type, institution_subtype, ownership,
                        courses_offered, fees, eligibility, admission_process, entrance_exam,
                        placement_rate, average_package, highest_package, ranking, facilities,
                        website, phone_number, email, admission_open_date, application_deadline,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb,
                        %s, %s, %s, %s, %s::jsonb,
                        %s, %s, %s, %s, %s,
                        NOW(), NOW()
                    )
                    ON CONFLICT (college_name) DO UPDATE SET
                        city = COALESCE(NULLIF(EXCLUDED.city, ''), colleges.city),
                        institution_type = COALESCE(NULLIF(EXCLUDED.institution_type, ''), colleges.institution_type),
                        institution_subtype = COALESCE(NULLIF(EXCLUDED.institution_subtype, ''), colleges.institution_subtype),
                        ownership = COALESCE(NULLIF(EXCLUDED.ownership, ''), colleges.ownership),
                        courses_offered = CASE
                            WHEN EXCLUDED.courses_offered = '[]'::jsonb THEN colleges.courses_offered
                            ELSE EXCLUDED.courses_offered
                        END,
                        fees = CASE
                            WHEN EXCLUDED.fees = '{}'::jsonb THEN colleges.fees
                            ELSE EXCLUDED.fees
                        END,
                        eligibility = CASE
                            WHEN EXCLUDED.eligibility = '{}'::jsonb THEN colleges.eligibility
                            ELSE EXCLUDED.eligibility
                        END,
                        admission_process = COALESCE(NULLIF(EXCLUDED.admission_process, ''), colleges.admission_process),
                        entrance_exam = CASE
                            WHEN EXCLUDED.entrance_exam = '[]'::jsonb THEN colleges.entrance_exam
                            ELSE EXCLUDED.entrance_exam
                        END,
                        placement_rate = COALESCE(EXCLUDED.placement_rate, colleges.placement_rate),
                        average_package = COALESCE(EXCLUDED.average_package, colleges.average_package),
                        highest_package = COALESCE(EXCLUDED.highest_package, colleges.highest_package),
                        ranking = COALESCE(NULLIF(EXCLUDED.ranking, ''), colleges.ranking),
                        facilities = CASE
                            WHEN EXCLUDED.facilities = '[]'::jsonb THEN colleges.facilities
                            ELSE EXCLUDED.facilities
                        END,
                        website = COALESCE(NULLIF(EXCLUDED.website, ''), colleges.website),
                        phone_number = COALESCE(NULLIF(EXCLUDED.phone_number, ''), colleges.phone_number),
                        email = COALESCE(NULLIF(EXCLUDED.email, ''), colleges.email),
                        admission_open_date = COALESCE(NULLIF(EXCLUDED.admission_open_date, ''), colleges.admission_open_date),
                        application_deadline = COALESCE(NULLIF(EXCLUDED.application_deadline, ''), colleges.application_deadline),
                        updated_at = NOW();
                """, (
                    c.get("college_name", ""),
                    c.get("city", ""),
                    c.get("institution_type", ""),
                    c.get("institution_subtype", ""),
                    c.get("ownership", ""),
                    _json_col(c.get("courses_offered", [])),
                    _json_col(c.get("fees", {})),
                    _json_col(c.get("eligibility", {})),
                    c.get("admission_process", ""),
                    _json_col(c.get("entrance_exam", [])),
                    c.get("placement_rate"),
                    c.get("average_package"),
                    c.get("highest_package"),
                    c.get("ranking", ""),
                    _json_col(c.get("facilities", [])),
                    c.get("website", ""),
                    c.get("phone_number", ""),
                    c.get("email", ""),
                    c.get("admission_open_date", ""),
                    c.get("application_deadline", ""),
                ))
        conn.commit()
        logger.info(f"Upserted {len(colleges)} colleges into PostgreSQL.")
    finally:
        conn.close()


def upsert_careers_batch(careers: list[dict]):
    """Batch upsert careers."""
    if not careers:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for c in careers:
                cur.execute("""
                    INSERT INTO careers (
                        career_name, also_known_as, category, description,
                        required_stream_class_11_12, path_after_10th, path_after_12th,
                        path_after_graduation, key_entrance_exams, primary_degree,
                        alternative_degrees, duration_years,
                        avg_salary_entry_inr, avg_salary_mid_inr, avg_salary_senior_inr,
                        top_companies, uttarakhand_colleges_offering,
                        skills_required, job_roles,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s::jsonb, %s, %s,
                        %s, %s, %s,
                        %s, %s::jsonb, %s,
                        %s::jsonb, %s,
                        %s, %s, %s,
                        %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb,
                        NOW(), NOW()
                    )
                    ON CONFLICT (career_name) DO UPDATE SET
                        also_known_as = CASE WHEN EXCLUDED.also_known_as = '[]'::jsonb THEN careers.also_known_as ELSE EXCLUDED.also_known_as END,
                        category = COALESCE(NULLIF(EXCLUDED.category, ''), careers.category),
                        description = COALESCE(NULLIF(EXCLUDED.description, ''), careers.description),
                        required_stream_class_11_12 = COALESCE(NULLIF(EXCLUDED.required_stream_class_11_12, ''), careers.required_stream_class_11_12),
                        path_after_10th = COALESCE(NULLIF(EXCLUDED.path_after_10th, ''), careers.path_after_10th),
                        path_after_12th = COALESCE(NULLIF(EXCLUDED.path_after_12th, ''), careers.path_after_12th),
                        path_after_graduation = COALESCE(NULLIF(EXCLUDED.path_after_graduation, ''), careers.path_after_graduation),
                        key_entrance_exams = CASE WHEN EXCLUDED.key_entrance_exams = '[]'::jsonb THEN careers.key_entrance_exams ELSE EXCLUDED.key_entrance_exams END,
                        primary_degree = COALESCE(NULLIF(EXCLUDED.primary_degree, ''), careers.primary_degree),
                        alternative_degrees = CASE WHEN EXCLUDED.alternative_degrees = '[]'::jsonb THEN careers.alternative_degrees ELSE EXCLUDED.alternative_degrees END,
                        duration_years = COALESCE(EXCLUDED.duration_years, careers.duration_years),
                        avg_salary_entry_inr = COALESCE(EXCLUDED.avg_salary_entry_inr, careers.avg_salary_entry_inr),
                        avg_salary_mid_inr = COALESCE(EXCLUDED.avg_salary_mid_inr, careers.avg_salary_mid_inr),
                        avg_salary_senior_inr = COALESCE(EXCLUDED.avg_salary_senior_inr, careers.avg_salary_senior_inr),
                        top_companies = CASE WHEN EXCLUDED.top_companies = '[]'::jsonb THEN careers.top_companies ELSE EXCLUDED.top_companies END,
                        uttarakhand_colleges_offering = CASE WHEN EXCLUDED.uttarakhand_colleges_offering = '[]'::jsonb THEN careers.uttarakhand_colleges_offering ELSE EXCLUDED.uttarakhand_colleges_offering END,
                        skills_required = CASE WHEN EXCLUDED.skills_required = '[]'::jsonb THEN careers.skills_required ELSE EXCLUDED.skills_required END,
                        job_roles = CASE WHEN EXCLUDED.job_roles = '[]'::jsonb THEN careers.job_roles ELSE EXCLUDED.job_roles END,
                        updated_at = NOW();
                """, (
                    c.get("career_name", ""),
                    _json_col(c.get("also_known_as", [])),
                    c.get("category", ""),
                    c.get("description", ""),
                    c.get("required_stream_class_11_12", ""),
                    c.get("path_after_10th", ""),
                    c.get("path_after_12th", ""),
                    c.get("path_after_graduation", ""),
                    _json_col(c.get("key_entrance_exams", [])),
                    c.get("primary_degree", ""),
                    _json_col(c.get("alternative_degrees", [])),
                    c.get("duration_years"),
                    c.get("avg_salary_entry_inr"),
                    c.get("avg_salary_mid_inr"),
                    c.get("avg_salary_senior_inr"),
                    _json_col(c.get("top_companies", [])),
                    _json_col(c.get("uttarakhand_colleges_offering", [])),
                    _json_col(c.get("skills_required", [])),
                    _json_col(c.get("job_roles", [])),
                ))
        conn.commit()
        logger.info(f"Upserted {len(careers)} careers into PostgreSQL.")
    finally:
        conn.close()


def upsert_exams_batch(exams: list[dict]):
    """Batch upsert exams."""
    if not exams:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for e in exams:
                cur.execute("""
                    INSERT INTO exams (
                        exam_name, full_name, conducting_body, for_courses, for_colleges,
                        frequency, eligibility, exam_mode, total_marks, duration_hours,
                        subjects, official_website, uttarakhand_colleges_using, preparation_tips,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s::jsonb, %s,
                        %s, %s, %s, %s, %s,
                        %s::jsonb, %s, %s::jsonb, %s,
                        NOW(), NOW()
                    )
                    ON CONFLICT (exam_name) DO UPDATE SET
                        full_name = COALESCE(NULLIF(EXCLUDED.full_name, ''), exams.full_name),
                        conducting_body = COALESCE(NULLIF(EXCLUDED.conducting_body, ''), exams.conducting_body),
                        for_courses = CASE WHEN EXCLUDED.for_courses = '[]'::jsonb THEN exams.for_courses ELSE EXCLUDED.for_courses END,
                        for_colleges = COALESCE(NULLIF(EXCLUDED.for_colleges, ''), exams.for_colleges),
                        frequency = COALESCE(NULLIF(EXCLUDED.frequency, ''), exams.frequency),
                        eligibility = COALESCE(NULLIF(EXCLUDED.eligibility, ''), exams.eligibility),
                        exam_mode = COALESCE(NULLIF(EXCLUDED.exam_mode, ''), exams.exam_mode),
                        total_marks = COALESCE(EXCLUDED.total_marks, exams.total_marks),
                        duration_hours = COALESCE(EXCLUDED.duration_hours, exams.duration_hours),
                        subjects = CASE WHEN EXCLUDED.subjects = '[]'::jsonb THEN exams.subjects ELSE EXCLUDED.subjects END,
                        official_website = COALESCE(NULLIF(EXCLUDED.official_website, ''), exams.official_website),
                        uttarakhand_colleges_using = CASE WHEN EXCLUDED.uttarakhand_colleges_using = '[]'::jsonb THEN exams.uttarakhand_colleges_using ELSE EXCLUDED.uttarakhand_colleges_using END,
                        preparation_tips = COALESCE(NULLIF(EXCLUDED.preparation_tips, ''), exams.preparation_tips),
                        updated_at = NOW();
                """, (
                    e.get("exam_name", ""),
                    e.get("full_name", ""),
                    e.get("conducting_body", ""),
                    _json_col(e.get("for_courses", [])),
                    e.get("for_colleges", ""),
                    e.get("frequency", ""),
                    e.get("eligibility", ""),
                    e.get("exam_mode", ""),
                    e.get("total_marks"),
                    e.get("duration_hours"),
                    _json_col(e.get("subjects", [])),
                    e.get("official_website", ""),
                    _json_col(e.get("uttarakhand_colleges_using", [])),
                    e.get("preparation_tips", ""),
                ))
        conn.commit()
        logger.info(f"Upserted {len(exams)} exams into PostgreSQL.")
    finally:
        conn.close()


def upsert_scholarships_batch(scholarships: list[dict]):
    """Batch upsert scholarships."""
    if not scholarships:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for s in scholarships:
                cur.execute("""
                    INSERT INTO scholarships (
                        name, type, category, amount, eligibility, apply_at, deadline,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        NOW(), NOW()
                    )
                    ON CONFLICT (name) DO UPDATE SET
                        type = COALESCE(NULLIF(EXCLUDED.type, ''), scholarships.type),
                        category = COALESCE(NULLIF(EXCLUDED.category, ''), scholarships.category),
                        amount = COALESCE(NULLIF(EXCLUDED.amount, ''), scholarships.amount),
                        eligibility = COALESCE(NULLIF(EXCLUDED.eligibility, ''), scholarships.eligibility),
                        apply_at = COALESCE(NULLIF(EXCLUDED.apply_at, ''), scholarships.apply_at),
                        deadline = COALESCE(NULLIF(EXCLUDED.deadline, ''), scholarships.deadline),
                        updated_at = NOW();
                """, (
                    s.get("name", ""),
                    s.get("type", ""),
                    s.get("category", ""),
                    s.get("amount", ""),
                    s.get("eligibility", ""),
                    s.get("apply_at", ""),
                    s.get("deadline", ""),
                ))
        conn.commit()
        logger.info(f"Upserted {len(scholarships)} scholarships into PostgreSQL.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
#  Query helpers
# ---------------------------------------------------------------------------

def _row_to_dict(cur, row) -> dict:
    """Convert a database row to a dictionary using cursor column descriptions."""
    cols = [desc[0] for desc in cur.description]
    d = {}
    for col, val in zip(cols, row):
        # Skip internal auto-increment id
        if col in ("id", "created_at", "updated_at"):
            continue
        # Convert UUID to string for JSON serialization
        if col == "uuid" and val is not None:
            d[col] = str(val)
        else:
            d[col] = val
    return d


def get_all_colleges() -> list[dict]:
    """Retrieve all colleges from PostgreSQL."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM colleges ORDER BY college_name;")
            return [_row_to_dict(cur, row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_all_careers() -> list[dict]:
    """Retrieve all careers from PostgreSQL."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM careers ORDER BY career_name;")
            return [_row_to_dict(cur, row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_all_exams() -> list[dict]:
    """Retrieve all exams from PostgreSQL."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM exams ORDER BY exam_name;")
            return [_row_to_dict(cur, row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_all_scholarships() -> list[dict]:
    """Retrieve all scholarships from PostgreSQL."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM scholarships ORDER BY name;")
            return [_row_to_dict(cur, row) for row in cur.fetchall()]
    finally:
        conn.close()


def search_colleges(query=None, city=None, institution_type=None, course=None, max_fee=None) -> list[dict]:
    """Search colleges with optional filters, using parameterized SQL."""
    conditions = []
    params = []

    if city:
        conditions.append("city ILIKE %s")
        params.append(f"%{city}%")

    if institution_type:
        conditions.append("institution_type ILIKE %s")
        params.append(f"%{institution_type}%")

    if course:
        # JSONB array containment: check if any element contains the course string
        conditions.append(
            "EXISTS (SELECT 1 FROM jsonb_array_elements_text(courses_offered) AS elem WHERE elem ILIKE %s)"
        )
        params.append(f"%{course}%")

    if max_fee:
        # Check if any fee value in the JSONB dict is <= max_fee
        conditions.append(
            "EXISTS (SELECT 1 FROM jsonb_each_text(fees) AS kv WHERE kv.value::int <= %s)"
        )
        params.append(max_fee)

    if query:
        conditions.append(
            "(college_name ILIKE %s OR city ILIKE %s OR "
            "EXISTS (SELECT 1 FROM jsonb_array_elements_text(courses_offered) AS elem WHERE elem ILIKE %s))"
        )
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

    where = " AND ".join(conditions) if conditions else "TRUE"
    sql = f"SELECT * FROM colleges WHERE {where} ORDER BY college_name;"

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_row_to_dict(cur, row) for row in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
#  Seed from JSON (first-run migration)
# ---------------------------------------------------------------------------

def seed_from_json(data_dir: Path):
    """Load existing JSON files and upsert into PostgreSQL.
    Only called when tables are empty (first startup).
    """
    logger.info("Seeding PostgreSQL tables from JSON files...")

    # Colleges
    colleges_file = data_dir / "uttarakhand_colleges_db.json"
    if colleges_file.exists():
        with open(colleges_file, "r", encoding="utf-8") as f:
            colleges = json.load(f).get("colleges", [])
        upsert_colleges_batch(colleges)
        logger.info(f"Seeded {len(colleges)} colleges.")

    # Careers
    careers_file = data_dir / "career_paths.json"
    if careers_file.exists():
        with open(careers_file, "r", encoding="utf-8") as f:
            careers = json.load(f).get("careers", [])
        upsert_careers_batch(careers)
        logger.info(f"Seeded {len(careers)} careers.")

    # Exams
    exams_file = data_dir / "entrance_exams.json"
    if exams_file.exists():
        with open(exams_file, "r", encoding="utf-8") as f:
            exams = json.load(f).get("exams", [])
        upsert_exams_batch(exams)
        logger.info(f"Seeded {len(exams)} exams.")

    # Scholarships
    scholarships_file = data_dir / "scholarships.json"
    if scholarships_file.exists():
        with open(scholarships_file, "r", encoding="utf-8") as f:
            scholarships = json.load(f).get("scholarships", [])
        upsert_scholarships_batch(scholarships)
        logger.info(f"Seeded {len(scholarships)} scholarships.")

    logger.info("JSON -> PostgreSQL seeding complete.")
