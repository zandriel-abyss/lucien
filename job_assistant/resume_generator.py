from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic

from .models import Job


class ResumeGenerator:
    def __init__(self, master_resume_path: Path, profile_path: Path, output_dir: Path) -> None:
        self.master_resume_path = master_resume_path
        self.profile_path = profile_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_tailored_resume(self, job: Job) -> Path:
        master_resume = self.master_resume_path.read_text(encoding="utf-8")
        profile = self.profile_path.read_text(encoding="utf-8")
        prompt = self._resume_prompt(job, master_resume, profile)
        content = self._generate_with_claude(prompt)

        output_path = self.output_dir / f"{self._slug(job.company)}_{self._slug(job.title)}_resume.md"
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_with_claude(self, prompt: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return (
                "## Tailored Resume Draft\n\n"
                "Claude API key not found. Set `ANTHROPIC_API_KEY` and regenerate.\n\n"
                "### Headline\n- Senior Product Leader in Fintech and AI\n\n"
                "### Summary\n- Placeholder summary pending model generation.\n"
            )
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1800,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    @staticmethod
    def _resume_prompt(job: Job, master_resume: str, profile: str) -> str:
        return f"""
You are an executive resume strategist.
Task: Generate a tailored resume draft for this role while preserving factual accuracy.
Do not invent achievements, metrics, company names, dates, or technologies not present in the source data.

Output format:
1) Headline (1 line)
2) Tailored Summary (4-6 lines)
3) Top Skills (10 bullets)
4) Revised Experience Bullets (3-5 bullets per relevant role, concise)
5) Notes for Human Review (5 bullets where factual verification is needed)

Tone: senior product leader, crisp and strategic.

Job details:
- Company: {job.company}
- Title: {job.title}
- Location: {job.location}
- URL: {job.job_url}

Job description:
{job.job_description}

Profile JSON:
{profile}

Master resume:
{master_resume}
""".strip()

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


class CoverLetterGenerator:
    def __init__(self, master_resume_path: Path, profile_path: Path, output_dir: Path) -> None:
        self.master_resume_path = master_resume_path
        self.profile_path = profile_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_cover_letter(self, job: Job) -> Path:
        master_resume = self.master_resume_path.read_text(encoding="utf-8")
        profile = self.profile_path.read_text(encoding="utf-8")
        prompt = f"""
Write a concise motivation letter for a senior product leader role.
Tone: crisp, strategic, and direct. Avoid overly warm language.
Length: 180-250 words.
Do not invent facts beyond the resume/profile.

Company: {job.company}
Role: {job.title}
Location: {job.location}
Job description:
{job.job_description}

Profile:
{profile}

Master resume:
{master_resume}
""".strip()
        content = self._generate_with_claude(prompt)

        file_name = f"{self._slug(job.company)}_{self._slug(job.title)}_cover_letter.md"
        output_path = self.output_dir / file_name
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_with_claude(self, prompt: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return (
                "## Motivation Letter Draft\n\n"
                "Claude API key not found. Set `ANTHROPIC_API_KEY` and regenerate."
            )
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=700,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
