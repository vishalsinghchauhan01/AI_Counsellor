"""
Pydantic models that mirror the existing JSON data schemas.
Used for validation of scraped + merged data before writing to disk.
"""
from pydantic import BaseModel, field_validator
from typing import List, Dict, Optional


class CollegeSchema(BaseModel):
    college_name: str
    city: str = ""
    institution_type: str = ""
    institution_subtype: str = ""
    ownership: str = ""
    courses_offered: List[str] = []
    fees: Dict[str, int] = {}
    eligibility: Dict[str, str] = {}
    admission_process: str = ""
    entrance_exam: List[str] = []
    placement_rate: Optional[int] = None
    average_package: Optional[int] = None
    highest_package: Optional[int] = None
    ranking: str = ""
    facilities: List[str] = []
    website: str = ""
    phone_number: str = ""
    email: str = ""
    admission_open_date: str = ""
    application_deadline: str = ""

    @field_validator("placement_rate")
    @classmethod
    def validate_placement_rate(cls, v):
        if v is not None and not (0 <= v <= 100):
            return None
        return v

    @field_validator("average_package", "highest_package")
    @classmethod
    def validate_package(cls, v):
        if v is not None and not (0 <= v <= 100_000_000):
            return None
        return v


class CareerSchema(BaseModel):
    career_name: str
    also_known_as: List[str] = []
    category: str = ""
    description: str = ""
    required_stream_class_11_12: str = ""
    path_after_10th: str = ""
    path_after_12th: str = ""
    path_after_graduation: str = ""
    key_entrance_exams: List[str] = []
    primary_degree: str = ""
    alternative_degrees: List[str] = []
    duration_years: Optional[int] = None
    avg_salary_entry_inr: Optional[int] = None
    avg_salary_mid_inr: Optional[int] = None
    avg_salary_senior_inr: Optional[int] = None
    top_companies: List[str] = []
    uttarakhand_colleges_offering: List[str] = []
    skills_required: List[str] = []
    job_roles: List[str] = []


class ExamSchema(BaseModel):
    exam_name: str
    full_name: str = ""
    conducting_body: str = ""
    for_courses: List[str] = []
    for_colleges: str = ""
    frequency: str = ""
    eligibility: str = ""
    exam_mode: str = ""
    total_marks: Optional[int] = None
    duration_hours: Optional[float] = None
    subjects: List[str] = []
    official_website: str = ""
    uttarakhand_colleges_using: List[str] = []
    preparation_tips: str = ""


class ScholarshipSchema(BaseModel):
    name: str
    type: str = ""
    category: str = ""
    amount: str = ""
    eligibility: str = ""
    apply_at: str = ""
    deadline: str = ""
