from __future__ import annotations

import json
import os
import re
from pathlib import Path

from anthropic import Anthropic

from .models import FitScoreBreakdown


class FitScorer:
    CATEGORY_KEYWORDS = {
        "fintech_payments": ["fintech", "payments", "banking", "cards", "wallet", "psp"],
        "ai_data": ["ai", "ml", "machine learning", "data", "analytics", "experimentation"],
        "compliance_regtech": ["compliance", "regulatory", "risk", "aml", "kyc", "regtech"],
        "product_leadership": ["product strategy", "roadmap", "leadership", "cross-functional", "mentor"],
        "seniority": ["head of", "director", "vp", "principal", "senior", "lead"],
        "location_visa": ["amsterdam", "netherlands", "eu", "visa", "hybrid", "onsite", "remote"],
        "dutch_language_requirement": ["dutch", "nederlands"],
    }

    WEIGHTS = {
        "fintech_payments": 0.24,
        "ai_data": 0.14,
        "compliance_regtech": 0.2,
        "product_leadership": 0.19,
        "seniority": 0.1,
        "location_visa": 0.08,
        "dutch_language_requirement": 0.05,
    }

    def __init__(self, profile_path: Path) -> None:
        self.profile = self._load_profile(profile_path)

    def score(self, job_description: str, location: str) -> FitScoreBreakdown:
        jd = f"{job_description}\n{location}".lower()
        profile_blob = json.dumps(self.profile).lower()

        category_scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            raw_score = self._keyword_overlap_score(jd, profile_blob, keywords)
            category_scores[category] = raw_score

        # Penalize Dutch-language requirements when Dutch proficiency is missing.
        if (
            category_scores["dutch_language_requirement"] >= 50
            and "dutch" not in profile_blob
            and "nederlands" not in profile_blob
        ):
            category_scores["dutch_language_requirement"] = 20

        weighted = sum(int(category_scores[key] * weight) for key, weight in self.WEIGHTS.items())
        overall_score = min(max(weighted, 0), 100)
        recommendation = self._recommendation(overall_score)
        explanation = self._build_explanation(category_scores, overall_score, recommendation)

        return FitScoreBreakdown(
            fintech_payments=category_scores["fintech_payments"],
            ai_data=category_scores["ai_data"],
            compliance_regtech=category_scores["compliance_regtech"],
            product_leadership=category_scores["product_leadership"],
            seniority=category_scores["seniority"],
            location_visa=category_scores["location_visa"],
            dutch_language_requirement=category_scores["dutch_language_requirement"],
            overall_score=overall_score,
            recommendation=recommendation,
            explanation=explanation,
        )

    def score_with_rationale(self, job_description: str, location: str) -> FitScoreBreakdown:
        base = self.score(job_description=job_description, location=location)
        rationale = self._claude_rationale(job_description, location, base)
        if rationale:
            base.explanation = f"{base.explanation}\n\nAI rationale:\n{rationale}"
        return base

    @staticmethod
    def _load_profile(path: Path) -> dict:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _keyword_overlap_score(jd: str, profile_blob: str, keywords: list[str]) -> int:
        jd_hits = sum(1 for k in keywords if re.search(rf"\b{re.escape(k)}\b", jd))
        profile_hits = sum(1 for k in keywords if re.search(rf"\b{re.escape(k)}\b", profile_blob))
        if jd_hits == 0:
            return 70
        match_ratio = min(profile_hits / jd_hits, 1.0)
        return int(40 + 60 * match_ratio)

    @staticmethod
    def _recommendation(score: int) -> str:
        if score >= 75:
            return "Apply"
        if score >= 55:
            return "Maybe"
        return "Skip"

    @staticmethod
    def _build_explanation(category_scores: dict[str, int], overall: int, recommendation: str) -> str:
        labels = {
            "fintech_payments": "Fintech/payments",
            "ai_data": "AI/data",
            "compliance_regtech": "Compliance/regtech",
            "product_leadership": "Product leadership",
            "seniority": "Seniority",
            "location_visa": "Location/visa",
            "dutch_language_requirement": "Dutch language requirement",
        }
        parts = [f"Overall fit score: {overall}/100. Recommendation: {recommendation}."]
        for key, label in labels.items():
            parts.append(f"{label}: {category_scores[key]}/100.")
        return " ".join(parts)

    def _claude_rationale(
        self,
        job_description: str,
        location: str,
        base_score: FitScoreBreakdown,
    ) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return ""

        profile_json = json.dumps(self.profile, indent=2)
        prompt = f"""
You are a career strategy analyst for a senior fintech/product leader.
Given the deterministic score and profile below, produce a concise rationale.
Do not fabricate profile facts. Focus on trade-offs and risks.
Keep under 140 words.

Deterministic score:
- Overall: {base_score.overall_score}
- Recommendation: {base_score.recommendation}
- Fintech/payments: {base_score.fintech_payments}
- AI/data: {base_score.ai_data}
- Compliance/regtech: {base_score.compliance_regtech}
- Product leadership: {base_score.product_leadership}
- Seniority: {base_score.seniority}
- Location/visa: {base_score.location_visa}
- Dutch language requirement: {base_score.dutch_language_requirement}

Profile:
{profile_json}

Job location: {location}
Job description:
{job_description[:8000]}
""".strip()

        try:
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=260,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception:
            return ""
