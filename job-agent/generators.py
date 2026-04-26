from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from anthropic import Anthropic

from profile import PROFILE, RESUME_MODES, STAR_STORIES
from prompts import build_generation_prompt, build_system_prompt

OUTPUT_DIR = Path("outputs")


class GeneratorService:
    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None

    @property
    def api_available(self) -> bool:
        return bool(self.client)

    def generate_package(
        self,
        role_context: Dict[str, object],
        resume_mode: str,
        questions: List[str],
    ) -> str:
        if self.client:
            return self._generate_with_claude(role_context, resume_mode, questions)
        return self._generate_mock(role_context, resume_mode, questions)

    def _generate_with_claude(
        self,
        role_context: Dict[str, object],
        resume_mode: str,
        questions: List[str],
    ) -> str:
        prompt = build_generation_prompt(
            profile={
                "profile": PROFILE,
                "resume_mode": RESUME_MODES.get(resume_mode, {}),
                "star_stories": STAR_STORIES,
            },
            role_context=role_context,
            questions=questions,
        )

        response = self.client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=2200,
            temperature=0.3,
            system=build_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        )

        parts = []
        for item in response.content:
            if getattr(item, "type", None) == "text":
                parts.append(item.text)
        return "\n".join(parts).strip()

    def _generate_mock(
        self,
        role_context: Dict[str, object],
        resume_mode: str,
        questions: List[str],
    ) -> str:
        headlines = RESUME_MODES[resume_mode]["headlines"]
        summary_focus = RESUME_MODES[resume_mode]["focus"]

        q_section = "\n".join([f"- Q: {q}\n  A: Draft answer based on profile evidence." for q in questions]) or "- No questions provided."

        return f"""
## Tailored Headline
{headlines[0]}

## Tailored Summary
Senior fintech product leader with 11+ years across platform modernization, regulated systems, and AI-enabled product transformation. {summary_focus} Brings cross-market execution across US, EU, and APAC with measurable outcomes in adoption, operating efficiency, quality, and release speed.

## Top Skills
Product strategy; Platform modernization; Payments; Treasury; AML/KYC; Compliance workflows; AI product delivery; Portfolio leadership; API-first architecture; GTM execution; Stakeholder management; Cross-functional scaling.

## Tailored Experience Bullets
### SafeSend
- Led strategy and delivery for a 7-product financial platform across tax workflows, payments, treasury, and compliance.
- Re-architected fragmented legacy systems into a modular API-first platform for scale and maintainability.
- Drove 64% product adoption growth and 35% operational efficiency gains through platform and workflow redesign.
- Improved sprint velocity by 45%, reduced QA defects by 59%, and shortened release timelines by 15%.
- Enabled AML/CFT, GDPR, and DORA-aligned workflows with audit-ready controls.
- Supported ISO 20022-compatible processing across 50+ jurisdictions and cross-border operations.

### Anakin
- Built conversational AI onboarding for digital banks and PSPs integrating identity verification and compliance workflows.
- Improved onboarding adoption by 45% and reduced bounce from 85% to 60%.
- Designed NLP architecture with Dialogflow and Rasa, plus STT/VAD for voice-led interactions.

### Cognizant
- Built regulatory QA frameworks for SWIFT/ACH payment systems in high-volume banking environments.
- Reduced regression time by 60% while increasing coverage by 31%.
- Translated AML requirements into testable system specifications and traceable controls.

## Relevant Projects
- Noir fraud detection framework: explainable ML risk signals and compliance-ready scoring.
- AI treasury copilot: FX timing and liquidity support, validated with 15+ CFO interviews.

## ATS Keywords
{', '.join(role_context.get('keywords', [])) or 'payments, platform, aml, kyc, compliance, ai, data'}

## Cover Letter
Dear Hiring Team,

I am excited to apply for the {role_context.get('title', 'role')} role at {role_context.get('company', 'your company')}. I bring 11+ years of product leadership across fintech platforms, regulated financial systems, and AI-enabled transformation. At SafeSend, I led modernization of a seven-product compliance and payments platform, delivering measurable gains in adoption, efficiency, quality, and delivery speed while aligning with AML/CFT, GDPR, and DORA requirements.

Across previous roles, I have built AI-driven onboarding and risk-aware infrastructure that balances customer experience, technical rigor, and compliance obligations. I am especially motivated by opportunities where platform strategy, regulatory depth, and execution discipline must come together to drive business outcomes.

I would welcome the chance to discuss how my background can support your product and growth priorities.

Best regards,  
Zack

## Application Answers
{q_section}

## Follow-Up Email
Subject: Follow-up on {role_context.get('title', 'application')} application

Hi Hiring Team, I wanted to follow up on my application and reiterate my strong interest in the role. My background combines fintech product leadership, regulated systems execution, and measurable platform outcomes. Happy to share a concise portfolio of relevant work if useful.
""".strip()


def save_output(company: str, title: str, content: str, output_type: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_company = "".join(c for c in company.lower().replace(" ", "-") if c.isalnum() or c == "-")
    safe_title = "".join(c for c in title.lower().replace(" ", "-") if c.isalnum() or c == "-")
    filename = f"{ts}-{safe_company}-{safe_title}-{output_type}.md"
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    return str(path)
