"""
Normalizes raw scraped data from each source into the canonical schemas.
Handles field mapping, fee parsing, name cleaning, and missing-field defaults.
"""
import re
import logging

logger = logging.getLogger("scraper.normalizer")


# ---------- Fee / salary parsing ----------

def normalize_fee_string(fee_str: str) -> int | None:
    """Convert various fee formats to integer INR.
    Examples: '2.5 Lakhs' -> 250000, '₹2,50,000' -> 250000, '250000' -> 250000
    """
    if not fee_str:
        return None
    fee_str = str(fee_str)

    # Remove currency symbols
    cleaned = re.sub(r'[₹$,]', '', fee_str).strip()
    cleaned = re.sub(r'^(INR|Rs\.?)\s*', '', cleaned, flags=re.IGNORECASE).strip()

    match = re.match(r'([\d\.]+)\s*(lakh|lac|L|crore|cr|K)?', cleaned, re.IGNORECASE)
    if not match:
        return None

    try:
        amount = float(match.group(1))
        unit = (match.group(2) or "").lower()
        if unit in ("lakh", "lac", "l"):
            amount *= 100_000
        elif unit in ("crore", "cr"):
            amount *= 10_000_000
        elif unit == "k":
            amount *= 1_000
        result = int(amount)
        if 500 <= result <= 10_000_000:
            return result
    except (ValueError, OverflowError):
        pass
    return None


def normalize_salary(val) -> int | None:
    """Normalize salary to integer INR."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        v = int(val)
        return v if 10_000 <= v <= 100_000_000 else None
    return normalize_fee_string(str(val))


def normalize_percentage(val) -> int | None:
    """Normalize percentage to integer 0-100."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        v = int(val)
        return v if 0 <= v <= 100 else None
    match = re.search(r'(\d+)', str(val))
    if match:
        v = int(match.group(1))
        return v if 0 <= v <= 100 else None
    return None


# ---------- Name cleaning ----------

def normalize_college_name(name: str) -> str:
    """Clean up college name for display.
    Strips course names, ranking suffixes, review tags, and page-title junk.
    """
    if not name:
        return ""
    # Remove excessive whitespace
    name = " ".join(name.split())
    # Strip course-name + everything after (e.g., "B.Tech Computer Science...: Fees 2026")
    name = re.sub(
        r'\s+(?:B\.?\s*Tech|M\.?\s*Tech|MBA|BBA|BCA|MCA|MBBS|BDS|B\.?\s*Sc|M\.?\s*Sc|'
        r'B\.?\s*Com|M\.?\s*Com|B\.?\s*Arch|LLB|B\.?\s*Pharm|M\.?\s*Pharm|B\.?\s*Ed|'
        r'BPT|Ph\.?\s*D|Diploma|BA\b|MA\b)\b.*$',
        '', name, flags=re.IGNORECASE
    )
    # Strip "Ranking 2024/2025/2026" anywhere
    name = re.sub(r'\s+Ranking\s+\d{4}.*$', '', name, flags=re.IGNORECASE)
    # Strip "Reviews on Placements, Faculty..."
    name = re.sub(r'\s+Reviews\s+on\s+.*$', '', name, flags=re.IGNORECASE)
    # Strip "Courses & Fees 2026" pattern
    name = re.sub(r'\s+Courses\s*&\s*Fees.*$', '', name, flags=re.IGNORECASE)
    # Strip colon/pipe-prefixed suffixes
    name = re.sub(
        r'\s*[:\|]\s*(?:Admission|Fees|Courses|Reviews|Cutoff|Ranking|Placement|'
        r'Eligibility|Scholarships|Course|Fee|Rank|Result|Overview|Hostel).*$',
        '', name, flags=re.IGNORECASE
    )
    # Remove leading/trailing special chars
    name = name.strip(" -–—|,")
    return name


def normalize_career_name(name: str) -> str:
    """Clean career name. Strips 'How to Become a/an' prefix and page-title junk."""
    if not name:
        return ""
    name = " ".join(name.split())
    # Strip "How to Become a/an ..." prefix
    name = re.sub(r'^How\s+to\s+Become\s+(?:a|an)\s+', '', name, flags=re.IGNORECASE)
    # Strip colon/pipe suffixes like ": Salary, Skills, Career Path..."
    name = re.sub(
        r'\s*[:\|]\s*(?:Salary|Skills|Career|Job|Eligibility|Qualification|Scope|Course).*$',
        '', name, flags=re.IGNORECASE
    )
    # Strip trailing year
    name = re.sub(r'\s+20\d{2}\s*$', '', name)
    return name.strip(" -–—|,")


def normalize_exam_name(name: str) -> str:
    """Clean exam name. Strips page-title junk like 'Registration, Exam Date, Admit Card...'"""
    if not name:
        return ""
    name = " ".join(name.split())
    # Strip everything after the exam name pattern
    # e.g. "AME CEE 2026 Registration, Exam Date..." → "AME CEE 2026"
    # e.g. "CAT Exam Pattern 2025 - Topic Wise..." → "CAT Exam Pattern 2025"
    name = re.sub(
        r'\s*(?:Registration|Application\s+Form|Admit\s+Card|Exam\s+Date|Syllabus\s*&|'
        r'Check\s+Date|Time\s+Table|Hall\s+Ticket|Direct\s+Link|'
        r',\s*(?:Exam\s+Date|Admit|Registration|Syllabus|Pattern|Cutoff|Admission|Result)).*$',
        '', name, flags=re.IGNORECASE
    )
    # Strip " - Topic Wise, Marking Scheme..." pattern
    name = re.sub(
        r'\s*-\s*(?:Topic|Check|Download|Marking|Subject|Question).*$',
        '', name, flags=re.IGNORECASE
    )
    # Strip "(OUT)", "(Over)", "(Released)", "(Started)", "(Closed)" markers
    name = re.sub(r'\s*\((?:OUT|Over|Released|Started|Closed|Out)\)', '', name, flags=re.IGNORECASE)
    # Strip trailing colon
    name = re.sub(r'\s*:\s*$', '', name)
    # Remove non-exam entries like "List of Exams in India" or "Statistics: Mean, Median..."
    lower = name.lower().strip()
    if lower.startswith("list of") or lower.startswith("statistics"):
        return ""
    return name.strip(" -–—|,")


def canonical_key(name: str) -> str:
    """Generate a lowercase canonical key for dedup matching.
    Strips parenthetical abbreviations, common suffixes, etc.
    """
    if not name:
        return ""
    key = name.lower().strip()
    # Strip course names + everything after
    key = re.sub(
        r'\s+(?:b\.?\s*tech|m\.?\s*tech|mba|bba|bca|mca|mbbs|bds|b\.?\s*sc|m\.?\s*sc|'
        r'b\.?\s*com|m\.?\s*com|b\.?\s*arch|llb|b\.?\s*pharm|m\.?\s*pharm|b\.?\s*ed|'
        r'bpt|ph\.?\s*d|diploma|ba\b|ma\b)\b.*$',
        '', key
    )
    # Strip ranking/review suffixes
    key = re.sub(r'\s+ranking\s+\d{4}.*$', '', key)
    key = re.sub(r'\s+reviews\s+on\s+.*$', '', key)
    key = re.sub(r'\s+courses\s*&\s*fees.*$', '', key)
    # Strip colon/pipe-prefixed suffixes
    key = re.sub(
        r'\s*[:\|]\s*(?:admission|fees|courses|reviews|cutoff|ranking|placement|eligibility|scholarships|course|fee|rank|result|overview|hostel).*$',
        '', key
    )
    # Remove content in parentheses (abbreviations like "(IIT Roorkee)")
    key = re.sub(r'\([^)]*\)', '', key)
    # Remove common suffixes
    for suffix in [", uttarakhand", ", dehradun", ", roorkee", ", haridwar",
                   " university", " college", " institute"]:
        key = key.replace(suffix, "")
    # Normalize whitespace
    key = " ".join(key.split())
    return key.strip()


# ---------- List normalization ----------

def normalize_string_list(items) -> list[str]:
    """Ensure a list of non-empty strings."""
    if not items:
        return []
    if isinstance(items, str):
        return [items.strip()] if items.strip() else []
    return [str(s).strip() for s in items if s and str(s).strip()]


def normalize_string_dict(d) -> dict[str, str]:
    """Ensure a dict of string keys and string values."""
    if not d or not isinstance(d, dict):
        return {}
    return {str(k).strip(): str(v).strip() for k, v in d.items() if k and v}


def normalize_fee_dict(d) -> dict[str, int]:
    """Ensure a dict of course name -> integer fee."""
    if not d or not isinstance(d, dict):
        return {}
    result = {}
    for k, v in d.items():
        k = str(k).strip()
        if not k:
            continue
        if isinstance(v, (int, float)):
            iv = int(v)
            if 500 <= iv <= 10_000_000:
                result[k] = iv
        elif isinstance(v, str):
            iv = normalize_fee_string(v)
            if iv:
                result[k] = iv
    return result


# ---------- Per-source normalization ----------

def normalize_college(raw: dict, source: str) -> dict:
    """Normalize a single college record to canonical schema."""
    return {
        "college_name": normalize_college_name(raw.get("college_name", "")),
        "city": (raw.get("city") or "").strip(),
        "institution_type": (raw.get("institution_type") or "").strip(),
        "institution_subtype": (raw.get("institution_subtype") or "").strip(),
        "ownership": (raw.get("ownership") or "").strip(),
        "courses_offered": normalize_string_list(raw.get("courses_offered")),
        "fees": normalize_fee_dict(raw.get("fees")),
        "eligibility": normalize_string_dict(raw.get("eligibility")),
        "admission_process": (raw.get("admission_process") or "").strip(),
        "entrance_exam": normalize_string_list(raw.get("entrance_exam")),
        "placement_rate": normalize_percentage(raw.get("placement_rate")),
        "average_package": normalize_salary(raw.get("average_package")),
        "highest_package": normalize_salary(raw.get("highest_package")),
        "ranking": (raw.get("ranking") or "").strip(),
        "facilities": normalize_string_list(raw.get("facilities")),
        "website": (raw.get("website") or "").strip(),
        "phone_number": (raw.get("phone_number") or "").strip(),
        "email": (raw.get("email") or "").strip(),
        "admission_open_date": (raw.get("admission_open_date") or "").strip(),
        "application_deadline": (raw.get("application_deadline") or "").strip(),
        "_source": source,
    }


def normalize_career(raw: dict, source: str) -> dict:
    """Normalize a single career record."""
    return {
        "career_name": normalize_career_name(raw.get("career_name", "")),
        "also_known_as": normalize_string_list(raw.get("also_known_as")),
        "category": (raw.get("category") or "").strip(),
        "description": (raw.get("description") or "").strip(),
        "required_stream_class_11_12": (raw.get("required_stream_class_11_12") or "").strip(),
        "path_after_10th": (raw.get("path_after_10th") or "").strip(),
        "path_after_12th": (raw.get("path_after_12th") or "").strip(),
        "path_after_graduation": (raw.get("path_after_graduation") or "").strip(),
        "key_entrance_exams": normalize_string_list(raw.get("key_entrance_exams")),
        "primary_degree": (raw.get("primary_degree") or "").strip(),
        "alternative_degrees": normalize_string_list(raw.get("alternative_degrees")),
        "duration_years": raw.get("duration_years") if isinstance(raw.get("duration_years"), int) else None,
        "avg_salary_entry_inr": normalize_salary(raw.get("avg_salary_entry_inr")),
        "avg_salary_mid_inr": normalize_salary(raw.get("avg_salary_mid_inr")),
        "avg_salary_senior_inr": normalize_salary(raw.get("avg_salary_senior_inr")),
        "top_companies": normalize_string_list(raw.get("top_companies")),
        "uttarakhand_colleges_offering": normalize_string_list(raw.get("uttarakhand_colleges_offering")),
        "skills_required": normalize_string_list(raw.get("skills_required")),
        "job_roles": normalize_string_list(raw.get("job_roles")),
        "_source": source,
    }


def normalize_exam(raw: dict, source: str) -> dict:
    """Normalize a single exam record."""
    return {
        "exam_name": normalize_exam_name(raw.get("exam_name", "")),
        "full_name": (raw.get("full_name") or "").strip(),
        "conducting_body": (raw.get("conducting_body") or "").strip(),
        "for_courses": normalize_string_list(raw.get("for_courses")),
        "for_colleges": (raw.get("for_colleges") or "").strip(),
        "frequency": (raw.get("frequency") or "").strip(),
        "eligibility": (raw.get("eligibility") or "").strip(),
        "exam_mode": (raw.get("exam_mode") or "").strip(),
        "total_marks": raw.get("total_marks") if isinstance(raw.get("total_marks"), int) else None,
        "duration_hours": raw.get("duration_hours") if isinstance(raw.get("duration_hours"), (int, float)) else None,
        "subjects": normalize_string_list(raw.get("subjects")),
        "official_website": (raw.get("official_website") or "").strip(),
        "uttarakhand_colleges_using": normalize_string_list(raw.get("uttarakhand_colleges_using")),
        "preparation_tips": (raw.get("preparation_tips") or "").strip(),
        "_source": source,
    }


def normalize_scholarship(raw: dict, source: str) -> dict:
    """Normalize a single scholarship record."""
    return {
        "name": (raw.get("name") or "").strip(),
        "type": (raw.get("type") or "").strip(),
        "category": (raw.get("category") or "").strip(),
        "amount": (raw.get("amount") or "").strip(),
        "eligibility": (raw.get("eligibility") or "").strip(),
        "apply_at": (raw.get("apply_at") or "").strip(),
        "deadline": (raw.get("deadline") or "").strip(),
        "_source": source,
    }


def normalize_source_data(source_result: dict) -> dict:
    """Normalize all data from a single source scraper result."""
    source = source_result["source"]
    return {
        "source": source,
        "colleges": [normalize_college(c, source) for c in source_result.get("colleges", []) if c.get("college_name")],
        "careers": [normalize_career(c, source) for c in source_result.get("careers", []) if c.get("career_name")],
        "exams": [normalize_exam(e, source) for e in source_result.get("exams", []) if e.get("exam_name")],
        "scholarships": [normalize_scholarship(s, source) for s in source_result.get("scholarships", []) if s.get("name")],
    }
