"""
Validates merged data against Pydantic schemas before writing to JSON.
Invalid records are logged and skipped.
"""
import logging
from scraper.schemas import CollegeSchema, CareerSchema, ExamSchema, ScholarshipSchema

logger = logging.getLogger("scraper.validator")


def _strip_internal_fields(record: dict) -> dict:
    """Remove internal fields (prefixed with _) before validation."""
    return {k: v for k, v in record.items() if not k.startswith("_")}


def validate_colleges(colleges: list[dict]) -> list[dict]:
    valid = []
    for c in colleges:
        try:
            clean = _strip_internal_fields(c)
            validated = CollegeSchema(**clean)
            valid.append(validated.model_dump())
        except Exception as e:
            logger.warning(f"College validation failed for '{c.get('college_name', '?')}': {e}")
    logger.info(f"Validated {len(valid)}/{len(colleges)} colleges")
    return valid


def validate_careers(careers: list[dict]) -> list[dict]:
    valid = []
    for c in careers:
        try:
            clean = _strip_internal_fields(c)
            validated = CareerSchema(**clean)
            valid.append(validated.model_dump())
        except Exception as e:
            logger.warning(f"Career validation failed for '{c.get('career_name', '?')}': {e}")
    logger.info(f"Validated {len(valid)}/{len(careers)} careers")
    return valid


def validate_exams(exams: list[dict]) -> list[dict]:
    valid = []
    for e in exams:
        try:
            clean = _strip_internal_fields(e)
            validated = ExamSchema(**clean)
            valid.append(validated.model_dump())
        except Exception as ex:
            logger.warning(f"Exam validation failed for '{e.get('exam_name', '?')}': {ex}")
    logger.info(f"Validated {len(valid)}/{len(exams)} exams")
    return valid


def validate_scholarships(scholarships: list[dict]) -> list[dict]:
    valid = []
    for s in scholarships:
        try:
            clean = _strip_internal_fields(s)
            validated = ScholarshipSchema(**clean)
            valid.append(validated.model_dump())
        except Exception as e:
            logger.warning(f"Scholarship validation failed for '{s.get('name', '?')}': {e}")
    logger.info(f"Validated {len(valid)}/{len(scholarships)} scholarships")
    return valid
