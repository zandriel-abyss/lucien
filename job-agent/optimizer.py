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

KEY_PHRASES = [
    "transaction monitoring",
    "financial crime",
    "cross-border payments",
    "product strategy",
    "platform modernization",
    "api-first",
    "risk scoring",
    "compliance workflows",
    "stakeholder management",
    "aml kyc",
    "identity verification",
]


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
    jd_text = (job_description or "").lower()
    jd_keywords = extract_jd_keywords(job_description)
    jd_phrases = [p for p in KEY_PHRASES if p in jd_text]

    profile_text = str(PROFILE).lower()
    matched_keywords = [k for k in jd_keywords if k in PROFILE_KEYWORDS]
    missing_keywords = [k for k in jd_keywords if k not in PROFILE_KEYWORDS][:10]
    matched_phrases = [p for p in jd_phrases if p in profile_text]
    missing_phrases = [p for p in jd_phrases if p not in profile_text][:6]

    total_terms = len(jd_keywords) + len(jd_phrases)
    total_matched = len(matched_keywords) + len(matched_phrases)
    coverage = int(round((total_matched / max(total_terms, 1)) * 100))

    suggestions = [
        f"Emphasize experience related to '{kw}' with factual SafeSend/Anakin examples."
        for kw in missing_keywords[:5]
    ]
    suggestions.extend(
        [f"Add a concise bullet that directly references phrase '{ph}' if truthfully applicable." for ph in missing_phrases[:3]]
    )

    return {
        "jd_keywords": jd_keywords,
        "jd_phrases": jd_phrases,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "matched_phrases": matched_phrases,
        "missing_phrases": missing_phrases,
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
