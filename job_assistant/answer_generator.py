from __future__ import annotations

import os
import re
from pathlib import Path

from anthropic import Anthropic

from .models import Job


class ApplicationAnswerGenerator:
    def __init__(self, profile_path: Path, star_stories_path: Path, output_dir: Path) -> None:
        self.profile_path = profile_path
        self.star_stories_path = star_stories_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_answers(self, job: Job, questions: str) -> Path:
        profile = self.profile_path.read_text(encoding="utf-8")
        stories = self.star_stories_path.read_text(encoding="utf-8")
        prompt = f"""
Draft concise, role-specific application answers.
Use only factual information from profile and STAR stories.
Keep each answer under 140 words unless the prompt asks otherwise.
Use strategic, senior-product-leader tone.

Role context:
- Company: {job.company}
- Title: {job.title}
- Location: {job.location}
- Job description:
{job.job_description}

Profile:
{profile}

STAR stories:
{stories}

Questions:
{questions}
""".strip()
        content = self._generate_with_claude(prompt)

        output_path = self.output_dir / f"{self._slug(job.company)}_{self._slug(job.title)}_qa.md"
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_with_claude(self, prompt: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "Claude API key not found. Set `ANTHROPIC_API_KEY` and regenerate."
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1400,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
