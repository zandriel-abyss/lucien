from __future__ import annotations

import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


@dataclass
class IntakeResult:
    title: str
    description: str
    company: str
    location: str
    source: str


class JobIntakeService:
    def fetch_from_url(self, url: str, source: str = "web") -> IntakeResult:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = self._extract_title(soup)
        description = self._extract_description(soup)
        company, location = self._extract_company_location(soup, description)

        return IntakeResult(
            title=title,
            description=description,
            company=company,
            location=location,
            source=source,
        )

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        if soup.title and soup.title.text.strip():
            return soup.title.text.strip()[:120]
        h1 = soup.find("h1")
        if h1 and h1.text.strip():
            return h1.text.strip()[:120]
        return "Unknown Role"

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str:
        # Drop script/style noise before text extraction.
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()

        candidates = []
        for selector in [
            "main",
            "[role='main']",
            ".job-description",
            ".description",
            "article",
            "section",
        ]:
            for node in soup.select(selector):
                text = node.get_text("\n", strip=True)
                if len(text) > 500:
                    candidates.append(text)

        if candidates:
            return max(candidates, key=len)[:12000]

        full_text = soup.get_text("\n", strip=True)
        return full_text[:12000]

    @staticmethod
    def _extract_company_location(soup: BeautifulSoup, description: str) -> tuple[str, str]:
        meta_company = soup.find("meta", attrs={"property": "og:site_name"})
        company = meta_company["content"].strip() if meta_company and meta_company.get("content") else "Unknown Company"

        location = "Unknown"
        location_match = re.search(
            r"\b(amsterdam|netherlands|rotterdam|utrecht|remote|hybrid|onsite|europe|eu)\b",
            description.lower(),
        )
        if location_match:
            location = location_match.group(1).title()
        return company[:120], location
