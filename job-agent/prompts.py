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

Return markdown only using EXACT top-level sections and order:
1) ## Role Strategy
2) ## Tailored Resume
3) ## Cover Letter
4) ## Application Answers
5) ## Interview Prep

Detailed requirements:
- Role Strategy: positioning narrative (how Zack should position herself for this role).
- Tailored Resume:
  - Headline
  - Summary (120-180 words)
  - Top skills (10-14 items)
  - SafeSend bullets (6-8)
  - Anakin bullets (3-4)
  - Cognizant bullets (2-3)
  - Relevant project bullets
  - ATS keywords
- Cover Letter: concise, senior, factual.
- Application Answers: concise direct responses for each application question.
- Interview Prep:
  - likely interview questions
  - 3 STAR stories to use
  - key metrics to mention
  - questions to ask interviewer

Tone:
- senior, crisp, strategic
- factual and defensible
- avoid generic language and overclaiming
""".strip()
