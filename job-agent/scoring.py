from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

ROLE_CATEGORIES = [
    "Product / Platform / Payments",
    "RegTech / Compliance / AML",
    "AI Product / Data",
    "Consulting / Transformation",
    "General Leadership",
]

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Product / Platform / Payments": [
        "product manager",
        "staff product",
        "group product",
        "director product",
        "platform",
        "roadmap",
        "saas",
        "marketplace",
        "payments",
        "payouts",
        "treasury",
    ],
    "RegTech / Compliance / AML": [
        "aml",
        "kyc",
        "edd",
        "sanctions",
        "transaction monitoring",
        "financial crime",
        "fiu",
        "compliance",
        "regtech",
        "risk controls",
    ],
    "AI Product / Data": [
        "ai",
        "ml",
        "llm",
        "data strategy",
        "analytics",
        "model",
        "automation",
        "machine learning",
    ],
    "Consulting / Transformation": [
        "consulting",
        "transformation",
        "operating model",
        "c-suite",
        "strategy",
        "cloud",
        "finops",
        "advisory",
    ],
    "General Leadership": [
        "head of",
        "vp",
        "executive",
        "leadership",
        "portfolio",
        "cross-functional",
    ],
}

WEIGHTS = {
    "seniority": 20,
    "domain": 25,
    "product_leadership": 20,
    "technical_ai_data": 15,
    "compliance_regulatory": 10,
    "location": 10,
}


@dataclass
class FitResult:
    score: int
    recommendation: str
    strengths: List[str]
    gaps: List[str]
    keywords: List[str]
    resume_mode: str
    breakdown: Dict[str, int]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def keyword_hits(text: str, keywords: List[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def classify_role(job_text: str) -> str:
    text = normalize(job_text)

    has_payments = any(k in text for k in ["payments", "payouts", "treasury", "iso 20022"])
    has_compliance = any(k in text for k in ["aml", "kyc", "edd", "compliance", "financial crime", "sanctions"])

    if has_payments and has_compliance:
        return "RegTech / Compliance / AML"

    category_scores = {
        category: keyword_hits(text, kws)
        for category, kws in CATEGORY_KEYWORDS.items()
    }
    best = max(category_scores, key=category_scores.get)

    if category_scores[best] == 0:
        return "General Leadership"
    return best


def infer_resume_mode(category: str, text: str) -> str:
    text_n = normalize(text)
    has_payments = any(k in text_n for k in ["payments", "payouts", "treasury", "platform"])
    has_compliance = any(k in text_n for k in ["aml", "kyc", "edd", "financial crime", "compliance", "regtech"])

    if has_payments and has_compliance:
        return "hybrid"
    if category == "RegTech / Compliance / AML":
        return "regtech"
    if category in ("AI Product / Data", "Consulting / Transformation") and has_compliance:
        return "hybrid"
    return "general"


def recommendation_from_score(score: int) -> str:
    if score >= 80:
        return "Strong Apply"
    if score >= 65:
        return "Apply"
    if score >= 45:
        return "Maybe"
    return "Skip"


def _score_bucket(hits: int, max_hits: int, weight: int) -> int:
    if max_hits <= 0:
        return 0
    ratio = min(hits / max_hits, 1.0)
    return int(round(ratio * weight))


def score_fit(job_title: str, location: str, job_description: str, category: str) -> FitResult:
    text = normalize(" ".join([job_title or "", location or "", job_description or ""]))

    seniority_hits = keyword_hits(text, ["senior", "staff", "lead", "principal", "director", "head", "vp"])
    domain_hits = keyword_hits(text, ["fintech", "payments", "banking", "treasury", "bfsi", "financial", "platform"])
    product_hits = keyword_hits(text, ["roadmap", "product strategy", "stakeholder", "gtm", "portfolio", "discovery", "delivery"])
    tech_ai_hits = keyword_hits(text, ["ai", "ml", "data", "analytics", "model", "automation", "api"])
    compliance_hits = keyword_hits(text, ["aml", "kyc", "compliance", "regulatory", "dora", "gdpr", "risk", "financial crime"])
    location_hits = keyword_hits(text, ["netherlands", "amsterdam", "europe", "eu", "global", "remote", "english"])

    breakdown = {
        "seniority": _score_bucket(seniority_hits, 5, WEIGHTS["seniority"]),
        "domain": _score_bucket(domain_hits, 6, WEIGHTS["domain"]),
        "product_leadership": _score_bucket(product_hits, 6, WEIGHTS["product_leadership"]),
        "technical_ai_data": _score_bucket(tech_ai_hits, 6, WEIGHTS["technical_ai_data"]),
        "compliance_regulatory": _score_bucket(compliance_hits, 6, WEIGHTS["compliance_regulatory"]),
        "location": _score_bucket(location_hits, 4, WEIGHTS["location"]),
    }

    score = sum(breakdown.values())
    recommendation = recommendation_from_score(score)
    resume_mode = infer_resume_mode(category, text)

    strengths = []
    if breakdown["domain"] >= 15:
        strengths.append("Strong fintech/payments domain relevance.")
    if breakdown["product_leadership"] >= 12:
        strengths.append("High product strategy and leadership overlap.")
    if breakdown["seniority"] >= 12:
        strengths.append("Role seniority aligns with 11+ years experience.")
    if breakdown["technical_ai_data"] >= 8:
        strengths.append("Meaningful AI/data product alignment.")
    if breakdown["compliance_regulatory"] >= 6:
        strengths.append("Compliance/regulatory context is a match.")

    if not strengths:
        strengths = ["General leadership and platform background is still relevant."]

    gaps = []
    if "onsite" in text and "amsterdam" not in text and "remote" not in text:
        gaps.append("Location constraints may need clarification.")
    if "german" in text and "german" not in "english dutch":
        gaps.append("Language expectation may need confirmation.")
    if breakdown["compliance_regulatory"] < 4 and category == "RegTech / Compliance / AML":
        gaps.append("JD stresses compliance depth more than explicit keywords matched.")
    if breakdown["technical_ai_data"] < 5 and category == "AI Product / Data":
        gaps.append("JD appears strongly AI-heavy; frame adjacent AI delivery experience.")

    if not gaps:
        gaps = [
            "Confirm exact scope ownership and team size expectations.",
            "Validate location/visa logistics if role is country-restricted.",
            "Confirm must-have tools or domain certifications if listed.",
        ]

    keyword_pool = set(re.findall(r"\b[a-z][a-z0-9\-\+]{2,}\b", text))
    priority_terms = [
        "payments",
        "platform",
        "roadmap",
        "leadership",
        "fintech",
        "compliance",
        "aml",
        "kyc",
        "risk",
        "ai",
        "data",
        "treasury",
        "gtm",
        "stakeholder",
    ]
    keywords = [k for k in priority_terms if k in keyword_pool][:12]

    return FitResult(
        score=score,
        recommendation=recommendation,
        strengths=strengths[:5],
        gaps=gaps[:3],
        keywords=keywords,
        resume_mode=resume_mode,
        breakdown=breakdown,
    )


def compute_priority_score(
    fit_score: int,
    recommendation: str,
    date_added: str | None,
    source: str | None,
    status: str | None,
) -> int:
    score = int(fit_score or 0)

    rec_bonus = {
        "Strong Apply": 20,
        "Apply": 12,
        "Maybe": 5,
        "Skip": -10,
    }.get((recommendation or "").strip(), 0)
    score += rec_bonus

    if (status or "") in {"Applied", "Interviewing", "Offer", "Archived", "Rejected"}:
        score -= 15

    source_txt = (source or "").lower()
    if "linkedin" in source_txt:
        score += 5
    elif "rss" in source_txt:
        score += 3

    if date_added:
        try:
            dt = datetime.fromisoformat(str(date_added).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600.0
            if age_hours <= 24:
                score += 12
            elif age_hours <= 72:
                score += 8
            elif age_hours <= 168:
                score += 4
        except Exception:
            pass

    return max(0, min(100, int(round(score))))
