from __future__ import annotations

from typing import Dict, List


def build_system_prompt() -> str:
    return (
        "You are an executive job application writing assistant for a senior fintech/product leader. "
        "Generate crisp, strategic, role-specific outputs. Keep claims factual and based only on provided profile data. "
        "Never invent employers, dates, certifications, or metrics. If a requested skill is missing, frame adjacent experience honestly."
    )


def build_generation_prompt(
    profile: Dict[str, object],
    role_context: Dict[str, object],
    questions: List[str],
) -> str:
    return f"""
Profile data (source of truth):
{profile}

Role context:
{role_context}

Application questions:
{questions}

Generate all of the following in markdown:
1) Tailored headline
2) Tailored summary (120-180 words)
3) Top skills (10-14 items)
4) Tailored experience bullets:
   - SafeSend: 6-8 bullets
   - Anakin: 3-4 bullets
   - Cognizant: 2-3 bullets
5) Relevant project bullets
6) ATS keywords list
7) Cover letter (concise, senior, factual)
8) Application answers for each question (concise, direct)
9) Optional follow-up email draft

Tone:
- senior, crisp, strategic
- factual and defensible
- avoid generic language
- no exaggerated confidence claims
""".strip()
