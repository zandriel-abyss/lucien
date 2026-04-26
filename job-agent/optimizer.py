from __future__ import annotations

import re
from typing import Dict, List

from profile import PROFILE

PROFILE_KEYWORDS = {
    "payments",
    "platform",
    "product",
    "roadmap",
    "leadership",
    "fintech",
    "aml",
    "kyc",
    "risk",
    "compliance",
    "ai",
    "data",
    "treasury",
    "api",
    "gtm",
    "stakeholder",
    "gdpr",
    "dora",
    "iso",
}

STOPWORDS = {
    "and",
    "the",
    "with",
    "for",
    "you",
    "are",
    "our",
    "this",
    "that",
    "from",
    "have",
    "will",
    "your",
    "role",
    "team",
    "into",
    "across",
    "using",
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b[a-z][a-z0-9\-]{2,}\b", (text or "").lower())


def extract_jd_keywords(job_description: str, limit: int = 25) -> List[str]:
    tokens = _tokenize(job_description)
    freq: Dict[str, int] = {}
    for t in tokens:
        if t in STOPWORDS:
            continue
        freq[t] = freq.get(t, 0) + 1

    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    keywords = [k for k, _ in ranked if k not in STOPWORDS]

    priority = [
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
        "stakeholder",
        "strategy",
        "api",
    ]

    ordered = []
    for p in priority:
        if p in keywords:
            ordered.append(p)
    for k in keywords:
        if k not in ordered:
            ordered.append(k)
    return ordered[:limit]


def ats_coverage_report(job_description: str) -> Dict[str, object]:
    jd_keywords = extract_jd_keywords(job_description)
    matched = [k for k in jd_keywords if k in PROFILE_KEYWORDS]
    missing = [k for k in jd_keywords if k not in PROFILE_KEYWORDS][:10]
    coverage = int(round((len(matched) / max(len(jd_keywords), 1)) * 100))

    suggestions = [
        f"Emphasize experience related to '{kw}' with factual SafeSend/Anakin examples."
        for kw in missing[:5]
    ]

    return {
        "jd_keywords": jd_keywords,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "coverage_percent": coverage,
        "suggestions": suggestions,
    }


def build_apply_checklist(company: str, title: str, job_url: str) -> List[str]:
    return [
        f"Open posting: {job_url or '[job URL missing]'}",
        f"Review tailored package for {title} at {company}",
        "Copy resume variant into final resume document",
        "Copy cover letter and adjust intro if needed",
        "Paste application answers into portal fields",
        "Complete mandatory fields and attachments",
        "Manual final review of claims and metrics",
        "Submit application manually",
        "Update tracker status to Applied and add timeline note",
    ]
