from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    SAVED = "saved"
    DRAFTED = "drafted"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


@dataclass
class Job:
    id: Optional[int]
    company: str
    title: str
    location: str
    job_url: str
    source: str
    date_added: str
    job_description: str
    fit_score: Optional[int] = None
    fit_recommendation: Optional[str] = None
    fit_explanation: Optional[str] = None
    status: JobStatus = JobStatus.SAVED
    follow_up_date: Optional[str] = None
    notes: str = ""


@dataclass
class FitScoreBreakdown:
    fintech_payments: int
    ai_data: int
    compliance_regtech: int
    product_leadership: int
    seniority: int
    location_visa: int
    dutch_language_requirement: int
    overall_score: int
    recommendation: str
    explanation: str


def utc_now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")
