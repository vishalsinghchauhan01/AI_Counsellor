"""
Deduplicates and merges records from multiple scraping sources + existing data.
Uses fuzzy name matching, content hashing, and trust-hierarchy-based conflict resolution.
Only updates records that actually changed — skips identical data.
"""
import hashlib
import json
import logging
from difflib import SequenceMatcher
from scraper.config import SOURCE_TRUST_ORDER
from scraper.normalizer import canonical_key, normalize_college_name

logger = logging.getLogger("scraper.deduplicator")

SIMILARITY_THRESHOLD = 0.85


# ---------- Content hashing ----------

def _hash_record(record: dict) -> str:
    """Generate a stable hash of a record's content (ignoring internal fields)."""
    clean = {k: v for k, v in sorted(record.items()) if not k.startswith("_")}
    return hashlib.md5(json.dumps(clean, sort_keys=True, default=str).encode()).hexdigest()


# ---------- Fuzzy matching ----------

def find_best_match(name: str, candidates: list[str]) -> str | None:
    """Find the best fuzzy match for a name among candidates."""
    key = canonical_key(name)
    if not key:
        return None
    best_score = 0.0
    best_match = None
    for candidate in candidates:
        ckey = canonical_key(candidate)
        if not ckey:
            continue
        # Exact match short-circuit
        if key == ckey:
            return candidate
        score = SequenceMatcher(None, key, ckey).ratio()
        if score > best_score:
            best_score = score
            best_match = candidate
    return best_match if best_score >= SIMILARITY_THRESHOLD else None


def _trust_rank(source: str) -> int:
    """Higher rank = more trusted."""
    try:
        return SOURCE_TRUST_ORDER.index(source)
    except ValueError:
        return -1


# ---------- Merge helpers ----------

def _pick_best_string(values_by_source: dict[str, str]) -> str:
    """Pick the non-empty string from the most trusted source."""
    # Always prefer "existing" data first (our curated data)
    if values_by_source.get("existing"):
        return values_by_source["existing"]
    for source in reversed(SOURCE_TRUST_ORDER):
        val = values_by_source.get(source, "")
        if val:
            return val
    for val in values_by_source.values():
        if val:
            return val
    return ""


def _pick_best_optional_int(values_by_source: dict[str, int | None]) -> int | None:
    """Prefer existing data, then most trusted, then average."""
    # Prefer existing curated data
    if values_by_source.get("existing") is not None:
        return values_by_source["existing"]
    non_null = {s: v for s, v in values_by_source.items() if v is not None and s != "existing"}
    if not non_null:
        return None
    if len(non_null) == 1:
        return list(non_null.values())[0]
    return int(sum(non_null.values()) / len(non_null))


def _union_lists(lists_by_source: dict[str, list]) -> list:
    """Union of all lists, deduped case-insensitively, existing data first."""
    seen = set()
    result = []
    # Existing first
    for item in lists_by_source.get("existing", []):
        lower = item.lower() if isinstance(item, str) else str(item)
        if lower not in seen:
            seen.add(lower)
            result.append(item)
    # Then by trust order
    for source in reversed(SOURCE_TRUST_ORDER):
        for item in lists_by_source.get(source, []):
            lower = item.lower() if isinstance(item, str) else str(item)
            if lower not in seen:
                seen.add(lower)
                result.append(item)
    # Remaining
    for source, items in lists_by_source.items():
        if source in ("existing",) or source in SOURCE_TRUST_ORDER:
            continue
        for item in items:
            lower = item.lower() if isinstance(item, str) else str(item)
            if lower not in seen:
                seen.add(lower)
                result.append(item)
    return result


def _merge_dicts(dicts_by_source: dict[str, dict]) -> dict:
    """Merge dicts, existing data wins, then most trusted."""
    result = {}
    # Existing first
    for k, v in dicts_by_source.get("existing", {}).items():
        if v:
            result[k] = v
    # Then trust order
    for source in SOURCE_TRUST_ORDER:
        d = dicts_by_source.get(source, {})
        for k, v in d.items():
            if v and (k not in result or not result[k]):
                result[k] = v
    return result


# ---------- Record merge ----------

def merge_college_group(records: list[dict], existing: dict | None = None) -> dict:
    """Merge multiple college records (from different sources) into one."""
    if not records and not existing:
        return {}

    all_records = list(records)
    if existing:
        existing_copy = dict(existing)
        existing_copy["_source"] = "existing"
        all_records.insert(0, existing_copy)

    name = ""
    if existing:
        name = existing.get("college_name", "")
    if not name:
        name = _pick_best_string({r.get("_source", ""): r.get("college_name", "") for r in all_records})

    # Ensure the final merged name is clean (removes titles like "Ranking 2026", "Fees 2026", etc.)
    name = normalize_college_name(name)

    by_src = lambda field: {r.get("_source", ""): r.get(field, "") for r in all_records}
    by_src_list = lambda field: {r.get("_source", ""): r.get(field, []) for r in all_records}
    by_src_dict = lambda field: {r.get("_source", ""): r.get(field, {}) for r in all_records}
    by_src_opt = lambda field: {r.get("_source", ""): r.get(field) for r in all_records}

    return {
        "college_name": name,
        "city": _pick_best_string(by_src("city")),
        "institution_type": _pick_best_string(by_src("institution_type")),
        "institution_subtype": _pick_best_string(by_src("institution_subtype")),
        "ownership": _pick_best_string(by_src("ownership")),
        "courses_offered": _union_lists(by_src_list("courses_offered")),
        "fees": _merge_dicts(by_src_dict("fees")),
        "eligibility": _merge_dicts(by_src_dict("eligibility")),
        "admission_process": _pick_best_string(by_src("admission_process")),
        "entrance_exam": _union_lists(by_src_list("entrance_exam")),
        "placement_rate": _pick_best_optional_int(by_src_opt("placement_rate")),
        "average_package": _pick_best_optional_int(by_src_opt("average_package")),
        "highest_package": _pick_best_optional_int(by_src_opt("highest_package")),
        "ranking": _pick_best_string(by_src("ranking")),
        "facilities": _union_lists(by_src_list("facilities")),
        "website": _pick_best_string(by_src("website")),
        "phone_number": _pick_best_string(by_src("phone_number")),
        "email": _pick_best_string(by_src("email")),
        "admission_open_date": _pick_best_string(by_src("admission_open_date")),
        "application_deadline": _pick_best_string(by_src("application_deadline")),
    }


def merge_career_group(records: list[dict], existing: dict | None = None) -> dict:
    all_records = list(records)
    if existing:
        existing_copy = dict(existing)
        existing_copy["_source"] = "existing"
        all_records.insert(0, existing_copy)

    by_src = lambda f: {r.get("_source", ""): r.get(f, "") for r in all_records}
    by_src_list = lambda f: {r.get("_source", ""): r.get(f, []) for r in all_records}
    by_src_opt = lambda f: {r.get("_source", ""): r.get(f) for r in all_records}

    name = ""
    if existing:
        name = existing.get("career_name", "")
    if not name:
        name = _pick_best_string({r.get("_source", ""): r.get("career_name", "") for r in all_records})

    return {
        "career_name": name,
        "also_known_as": _union_lists(by_src_list("also_known_as")),
        "category": _pick_best_string(by_src("category")),
        "description": _pick_best_string(by_src("description")),
        "required_stream_class_11_12": _pick_best_string(by_src("required_stream_class_11_12")),
        "path_after_10th": _pick_best_string(by_src("path_after_10th")),
        "path_after_12th": _pick_best_string(by_src("path_after_12th")),
        "path_after_graduation": _pick_best_string(by_src("path_after_graduation")),
        "key_entrance_exams": _union_lists(by_src_list("key_entrance_exams")),
        "primary_degree": _pick_best_string(by_src("primary_degree")),
        "alternative_degrees": _union_lists(by_src_list("alternative_degrees")),
        "duration_years": _pick_best_optional_int(by_src_opt("duration_years")),
        "avg_salary_entry_inr": _pick_best_optional_int(by_src_opt("avg_salary_entry_inr")),
        "avg_salary_mid_inr": _pick_best_optional_int(by_src_opt("avg_salary_mid_inr")),
        "avg_salary_senior_inr": _pick_best_optional_int(by_src_opt("avg_salary_senior_inr")),
        "top_companies": _union_lists(by_src_list("top_companies")),
        "uttarakhand_colleges_offering": _union_lists(by_src_list("uttarakhand_colleges_offering")),
        "skills_required": _union_lists(by_src_list("skills_required")),
        "job_roles": _union_lists(by_src_list("job_roles")),
    }


def merge_exam_group(records: list[dict], existing: dict | None = None) -> dict:
    all_records = list(records)
    if existing:
        existing_copy = dict(existing)
        existing_copy["_source"] = "existing"
        all_records.insert(0, existing_copy)

    by_src = lambda f: {r.get("_source", ""): r.get(f, "") for r in all_records}
    by_src_list = lambda f: {r.get("_source", ""): r.get(f, []) for r in all_records}
    by_src_opt = lambda f: {r.get("_source", ""): r.get(f) for r in all_records}

    name = ""
    if existing:
        name = existing.get("exam_name", "")
    if not name:
        name = _pick_best_string({r.get("_source", ""): r.get("exam_name", "") for r in all_records})

    return {
        "exam_name": name,
        "full_name": _pick_best_string(by_src("full_name")),
        "conducting_body": _pick_best_string(by_src("conducting_body")),
        "for_courses": _union_lists(by_src_list("for_courses")),
        "for_colleges": _pick_best_string(by_src("for_colleges")),
        "frequency": _pick_best_string(by_src("frequency")),
        "eligibility": _pick_best_string(by_src("eligibility")),
        "exam_mode": _pick_best_string(by_src("exam_mode")),
        "total_marks": _pick_best_optional_int(by_src_opt("total_marks")),
        "duration_hours": _pick_best_optional_int(by_src_opt("duration_hours")),
        "subjects": _union_lists(by_src_list("subjects")),
        "official_website": _pick_best_string(by_src("official_website")),
        "uttarakhand_colleges_using": _union_lists(by_src_list("uttarakhand_colleges_using")),
        "preparation_tips": _pick_best_string(by_src("preparation_tips")),
    }


def merge_scholarship_group(records: list[dict], existing: dict | None = None) -> dict:
    all_records = list(records)
    if existing:
        existing_copy = dict(existing)
        existing_copy["_source"] = "existing"
        all_records.insert(0, existing_copy)

    by_src = lambda f: {r.get("_source", ""): r.get(f, "") for r in all_records}

    name = ""
    if existing:
        name = existing.get("name", "")
    if not name:
        name = _pick_best_string({r.get("_source", ""): r.get("name", "") for r in all_records})

    return {
        "name": name,
        "type": _pick_best_string(by_src("type")),
        "category": _pick_best_string(by_src("category")),
        "amount": _pick_best_string(by_src("amount")),
        "eligibility": _pick_best_string(by_src("eligibility")),
        "apply_at": _pick_best_string(by_src("apply_at")),
        "deadline": _pick_best_string(by_src("deadline")),
    }


# ---------- Main dedup + merge ----------

def _group_records(records: list[dict], name_field: str) -> dict[str, list[dict]]:
    """Group records by fuzzy-matched name. Returns {canonical_name: [records]}."""
    groups = {}
    name_to_canonical = {}

    for record in records:
        name = record.get(name_field, "")
        if not name:
            continue

        matched = find_best_match(name, list(name_to_canonical.keys()))
        if matched:
            canon = name_to_canonical[matched]
            groups[canon].append(record)
        else:
            name_to_canonical[name] = name
            groups[name] = [record]

    return groups


def deduplicate_and_merge(normalized_by_source: dict[str, dict], existing_data: dict) -> dict:
    """
    Deduplicate and merge data from all scraped sources + existing JSON data.
    Returns only changed/new data merged with existing. Existing data is preserved.
    """
    all_colleges = []
    all_careers = []
    all_exams = []
    all_scholarships = []
    for source_data in normalized_by_source.values():
        all_colleges.extend(source_data.get("colleges", []))
        all_careers.extend(source_data.get("careers", []))
        all_exams.extend(source_data.get("exams", []))
        all_scholarships.extend(source_data.get("scholarships", []))

    college_groups = _group_records(all_colleges, "college_name")
    career_groups = _group_records(all_careers, "career_name")
    exam_groups = _group_records(all_exams, "exam_name")
    schol_groups = _group_records(all_scholarships, "name")

    logger.info(
        f"Dedup groups: {len(college_groups)} colleges, {len(career_groups)} careers, "
        f"{len(exam_groups)} exams, {len(schol_groups)} scholarships"
    )

    existing_colleges = {c["college_name"]: c for c in existing_data.get("colleges", [])}
    existing_careers = {c["career_name"]: c for c in existing_data.get("careers", [])}
    existing_exams = {e["exam_name"]: e for e in existing_data.get("exams", [])}
    existing_schols = {s["name"]: s for s in existing_data.get("scholarships", [])}

    # --- Colleges ---
    merged_colleges = []
    used_existing = set()
    for group_name, records in college_groups.items():
        existing_match = None
        match_key = find_best_match(group_name, list(existing_colleges.keys()))
        if match_key:
            existing_match = existing_colleges[match_key]
            used_existing.add(match_key)
        merged = merge_college_group(records, existing_match)
        merged_colleges.append(merged)
    for name, college in existing_colleges.items():
        if name not in used_existing:
            merged_colleges.append(college)

    # --- Careers ---
    merged_careers = []
    used_existing = set()
    for group_name, records in career_groups.items():
        existing_match = None
        match_key = find_best_match(group_name, list(existing_careers.keys()))
        if match_key:
            existing_match = existing_careers[match_key]
            used_existing.add(match_key)
        merged = merge_career_group(records, existing_match)
        merged_careers.append(merged)
    for name, career in existing_careers.items():
        if name not in used_existing:
            merged_careers.append(career)

    # --- Exams ---
    merged_exams = []
    used_existing = set()
    for group_name, records in exam_groups.items():
        existing_match = None
        match_key = find_best_match(group_name, list(existing_exams.keys()))
        if match_key:
            existing_match = existing_exams[match_key]
            used_existing.add(match_key)
        merged = merge_exam_group(records, existing_match)
        merged_exams.append(merged)
    for name, exam in existing_exams.items():
        if name not in used_existing:
            merged_exams.append(exam)

    # --- Scholarships ---
    merged_schols = []
    used_existing = set()
    for group_name, records in schol_groups.items():
        existing_match = None
        match_key = find_best_match(group_name, list(existing_schols.keys()))
        if match_key:
            existing_match = existing_schols[match_key]
            used_existing.add(match_key)
        merged = merge_scholarship_group(records, existing_match)
        merged_schols.append(merged)
    for name, schol in existing_schols.items():
        if name not in used_existing:
            merged_schols.append(schol)

    logger.info(
        f"Merge complete: {len(merged_colleges)} colleges, {len(merged_careers)} careers, "
        f"{len(merged_exams)} exams, {len(merged_schols)} scholarships"
    )

    return {
        "colleges": merged_colleges,
        "careers": merged_careers,
        "exams": merged_exams,
        "scholarships": merged_schols,
    }


def has_data_changed(old_data: dict, new_data: dict) -> bool:
    """Compare old and new data by content hash. Returns True if anything changed."""
    old_hash = hashlib.md5(json.dumps(old_data, sort_keys=True, default=str).encode()).hexdigest()
    new_hash = hashlib.md5(json.dumps(new_data, sort_keys=True, default=str).encode()).hexdigest()
    return old_hash != new_hash
