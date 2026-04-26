from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - optional dependency at runtime
    Anthropic = None

from profile import PROFILE, RESUME_MODES, STAR_STORIES
from prompts import build_generation_prompt, build_system_prompt

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
SECTION_KEYS = ["role_strategy", "resume", "cover_letter", "application_answers", "interview_prep"]
SECTION_HEADINGS = {
    "role_strategy": "## Role Strategy",
    "resume": "## Tailored Resume",
    "cover_letter": "## Cover Letter",
    "application_answers": "## Application Answers",
    "interview_prep": "## Interview Prep",
}


class GeneratorService:
    def __init__(self) -> None:
        self.provider = (os.getenv("JOB_AGENT_LLM_PROVIDER") or "ollama").strip().lower()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key) if (self.api_key and Anthropic and self.provider == "anthropic") else None
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.ollama_base_url = (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL") or "llama3.1:8b"
        self.last_generation_mode = "mock"
        self.last_generation_error = ""

    @property
    def api_available(self) -> bool:
        if self.provider == "anthropic":
            return bool(self.client)
        if self.provider == "openai":
            return bool(self.openai_api_key)
        if self.provider == "ollama":
            return True
        return False

    def generate_package(
        self,
        role_context: Dict[str, object],
        resume_mode: str,
        questions: List[str],
    ) -> Dict[str, str]:
        try:
            if self.provider == "anthropic" and self.client:
                full = self._generate_with_claude(role_context, resume_mode, questions)
                self.last_generation_mode = "live-anthropic"
                self.last_generation_error = ""
            elif self.provider == "openai" and self.openai_api_key:
                full = self._generate_with_openai(role_context, resume_mode, questions)
                self.last_generation_mode = "live-openai"
                self.last_generation_error = ""
            elif self.provider == "ollama":
                full = self._generate_with_ollama(role_context, resume_mode, questions)
                self.last_generation_mode = "live-ollama"
                self.last_generation_error = ""
            else:
                raise RuntimeError("Configured LLM provider unavailable")
        except Exception as exc:
            full = self._generate_mock(role_context, resume_mode, questions)
            self.last_generation_mode = "mock"
            self.last_generation_error = str(exc)
        return split_sections(full)

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
            max_tokens=2400,
            temperature=0.3,
            system=build_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        )

        parts = []
        for item in response.content:
            if getattr(item, "type", None) == "text":
                parts.append(item.text)
        return "\n".join(parts).strip()

    def _generate_with_ollama(
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
        payload = {
            "model": self.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0.3},
        }
        req = Request(
            f"{self.ollama_base_url}/api/chat",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"Ollama connection failed: {exc}")
        content = ((body.get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("Ollama returned empty content")
        return content

    def _generate_with_openai(
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
        payload = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        req = Request(
            "https://api.openai.com/v1/chat/completions",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}",
            },
        )
        try:
            with urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"OpenAI connection failed: {exc}")
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI returned no choices")
        content = (((choices[0] or {}).get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("OpenAI returned empty content")
        return content

    def _generate_mock(
        self,
        role_context: Dict[str, object],
        resume_mode: str,
        questions: List[str],
    ) -> str:
        headlines = RESUME_MODES[resume_mode]["headlines"]
        summary_focus = RESUME_MODES[resume_mode]["focus"]
        keywords = ", ".join(role_context.get("keywords", [])) or "payments, platform, aml, kyc, compliance, ai, data"

        q_section = "\n".join([f"- **Q:** {q}\n  **A:** Draft answer based on profile evidence." for q in questions]) or "- No questions provided."

        return f"""
## Role Strategy
Position as a senior fintech product leader who can scale regulated platforms while improving operating metrics. Lead with SafeSend portfolio modernization outcomes, then reinforce AI-enabled risk and onboarding experience from Anakin and strategic projects. Emphasize cross-functional execution with compliance, engineering, and commercial stakeholders across US/EU/APAC.

## Tailored Resume
### Headline
{headlines[0]}

### Summary
Senior fintech product leader with 11+ years across platform modernization, regulated systems, and AI-enabled product transformation. {summary_focus} Brings cross-market execution across US, EU, and APAC with measurable outcomes in adoption, operating efficiency, quality, and release speed.

### Top Skills
Product strategy; Platform modernization; Payments; Treasury; AML/KYC; Compliance workflows; AI product delivery; Portfolio leadership; API-first architecture; GTM execution; Stakeholder management; Cross-functional scaling.

### Tailored Experience Bullets
#### SafeSend
- Led strategy and delivery for a 7-product financial platform across tax workflows, payments, treasury, and compliance.
- Re-architected fragmented legacy systems into a modular API-first platform for scale and maintainability.
- Drove 64% product adoption growth and 35% operational efficiency gains through platform and workflow redesign.
- Improved sprint velocity by 45%, reduced QA defects by 59%, and shortened release timelines by 15%.
- Enabled AML/CFT, GDPR, and DORA-aligned workflows with audit-ready controls.
- Supported ISO 20022-compatible processing across 50+ jurisdictions and cross-border operations.

#### Anakin
- Built conversational AI onboarding for digital banks and PSPs integrating identity verification and compliance workflows.
- Improved onboarding adoption by 45% and reduced bounce from 85% to 60%.
- Designed NLP architecture with Dialogflow and Rasa, plus STT/VAD for voice-led interactions.

#### Cognizant
- Built regulatory QA frameworks for SWIFT/ACH payment systems in high-volume banking environments.
- Reduced regression time by 60% while increasing coverage by 31%.
- Translated AML requirements into testable system specifications and traceable controls.

### Relevant Projects
- Noir fraud detection framework: explainable ML risk signals and compliance-ready scoring.
- AI treasury copilot: FX timing and liquidity support, validated with 15+ CFO interviews.

### ATS Keywords
{keywords}

## Cover Letter
Dear Hiring Team,

I am excited to apply for the {role_context.get('title', 'role')} role at {role_context.get('company', 'your company')}. I bring 11+ years of product leadership across fintech platforms, regulated financial systems, and AI-enabled transformation. At SafeSend, I led modernization of a seven-product compliance and payments platform, delivering measurable gains in adoption, efficiency, quality, and delivery speed while aligning with AML/CFT, GDPR, and DORA requirements.

Across previous roles, I have built AI-driven onboarding and risk-aware infrastructure that balances customer experience, technical rigor, and compliance obligations. I am especially motivated by opportunities where platform strategy, regulatory depth, and execution discipline must come together to drive business outcomes.

I would welcome the chance to discuss how my background can support your product and growth priorities.

Best regards,  
Zack

## Application Answers
{q_section}

## Interview Prep
### Likely Interview Questions
- Tell us about a platform modernization you led in a regulated environment.
- How do you prioritize roadmap trade-offs across product, compliance, and engineering?
- Describe your approach to AI-driven risk or onboarding systems.
- How do you define and track product impact at portfolio level?
- How do you align C-suite, compliance, and delivery teams on execution?

### STAR Stories to Use
- SafeSend Transformation
- Anakin Onboarding AI
- Noir Fraud Detection Framework

### Key Metrics to Mention
- 64% adoption growth
- 35% efficiency gains
- 45% sprint velocity improvement
- 59% QA defect reduction
- 15% faster release timelines

### Questions to Ask Interviewer
- What business outcomes define success for this role in the first 6-12 months?
- How are compliance and product priorities balanced in roadmap decisions?
- Where are the largest execution bottlenecks today across teams?
- Which customer or market segment is the top strategic focus this year?
""".strip()


def split_sections(content: str) -> Dict[str, str]:
    sections: Dict[str, str] = {k: "" for k in SECTION_KEYS}
    for idx, key in enumerate(SECTION_KEYS):
        heading = SECTION_HEADINGS[key]
        start = content.find(heading)
        if start == -1:
            continue
        start += len(heading)
        end = len(content)
        if idx + 1 < len(SECTION_KEYS):
            next_heading = SECTION_HEADINGS[SECTION_KEYS[idx + 1]]
            next_pos = content.find(next_heading, start)
            if next_pos != -1:
                end = next_pos
        sections[key] = content[start:end].strip()
    return sections


def save_output(company: str, title: str, content: str, output_type: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_company = "".join(c for c in company.lower().replace(" ", "-") if c.isalnum() or c == "-")
    safe_title = "".join(c for c in title.lower().replace(" ", "-") if c.isalnum() or c == "-")
    filename = f"{ts}-{safe_company}-{safe_title}-{output_type}.md"
    path = OUTPUT_DIR / filename
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return str(path)
