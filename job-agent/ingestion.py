from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


@dataclass
class IngestedJob:
    company: str
    title: str
    location: str
    job_url: str
    source: str
    job_description: str
    application_questions: str
    posted_at: Optional[str]


def _safe_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        clean_q = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), parsed.params, urlencode(clean_q), ""))
    except Exception:
        return raw


def _extract_company_from_url(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        host = host.replace("www.", "")
        return host.split(".")[0].title() if host else "Unknown"
    except Exception:
        return "Unknown"


def _extract_title_from_html(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return "Untitled Role"
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    title = re.split(r"\||-", title)[0].strip()
    return title or "Untitled Role"


def _extract_description_from_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 5000:
        return text[:5000] + "..."
    return text


def parse_csv_jobs(content: str, source: str = "CSV Import") -> List[IngestedJob]:
    rows: List[IngestedJob] = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        rows.append(
            IngestedJob(
                company=_safe_text(row.get("company")),
                title=_safe_text(row.get("title")),
                location=_safe_text(row.get("location")),
                job_url=_normalize_url(_safe_text(row.get("job_url") or row.get("url"))),
                source=source,
                job_description=_safe_text(row.get("job_description") or row.get("description")),
                application_questions=_safe_text(row.get("application_questions") or row.get("questions")),
                posted_at=_safe_text(row.get("posted_at")) or None,
            )
        )
    return rows


def parse_rss_jobs(rss_url: str, source: str = "RSS") -> List[IngestedJob]:
    req = Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch RSS feed: {exc}")

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise RuntimeError(f"Invalid RSS/Atom XML: {exc}")

    jobs: List[IngestedJob] = []

    # RSS 2.0
    for item in root.findall(".//item"):
        title = _safe_text(item.findtext("title"))
        link = _safe_text(item.findtext("link"))
        desc = _safe_text(item.findtext("description"))
        pub = _safe_text(item.findtext("pubDate")) or None
        jobs.append(
            IngestedJob(
                company=_extract_company_from_url(link),
                title=title or "Untitled Role",
                location="",
                job_url=_normalize_url(link),
                source=source,
                job_description=desc,
                application_questions="",
                posted_at=pub,
            )
        )

    # Atom
    if not jobs:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//a:entry", ns):
            title = _safe_text(entry.findtext("a:title", default="", namespaces=ns))
            link_el = entry.find("a:link", ns)
            link = _safe_text(link_el.get("href") if link_el is not None else "")
            summary = _safe_text(entry.findtext("a:summary", default="", namespaces=ns))
            updated = _safe_text(entry.findtext("a:updated", default="", namespaces=ns)) or None
            jobs.append(
                IngestedJob(
                    company=_extract_company_from_url(link),
                    title=title or "Untitled Role",
                    location="",
                    job_url=_normalize_url(link),
                    source=source,
                    job_description=summary,
                    application_questions="",
                    posted_at=updated,
                )
            )

    return jobs


def parse_job_from_url(job_url: str, source: str = "Manual Career URL") -> IngestedJob:
    req = Request(job_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch URL: {exc}")

    title = _extract_title_from_html(html)
    description = _extract_description_from_html(html)
    company = _extract_company_from_url(job_url)

    return IngestedJob(
        company=company,
        title=title,
        location="",
        job_url=_normalize_url(job_url),
        source=source,
        job_description=description,
        application_questions="",
        posted_at=None,
    )


def parse_relative_window(window: str) -> timedelta:
    token = window.strip().lower()
    if token in {"24h", "1d"}:
        return timedelta(days=1)
    if token in {"3d", "72h"}:
        return timedelta(days=3)
    if token in {"7d", "1w", "week"}:
        return timedelta(days=7)
    return timedelta(days=30)


def parse_datetime(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None

    raw = text.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def filter_recent_jobs(jobs: List[IngestedJob], window: str) -> List[IngestedJob]:
    delta = parse_relative_window(window)
    cutoff = datetime.now(timezone.utc) - delta

    filtered: List[IngestedJob] = []
    for job in jobs:
        parsed = parse_datetime(job.posted_at)
        if parsed is None:
            # Keep unknown dates so user can decide manually.
            filtered.append(job)
        elif parsed >= cutoff:
            filtered.append(job)
    return filtered


def dedupe_jobs(
    jobs: List[IngestedJob],
    existing_rows: List[Dict[str, object]],
) -> List[IngestedJob]:
    existing_keys = {
        (
            (str(r.get("company") or "").strip().lower()),
            (str(r.get("title") or "").strip().lower()),
            (str(r.get("job_url") or "").strip().lower()),
        )
        for r in existing_rows
    }
    out: List[IngestedJob] = []
    seen = set()
    for job in jobs:
        key = (job.company.lower(), job.title.lower(), job.job_url.lower())
        if key in existing_keys or key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out


def normalize_ingested_jobs(jobs: List[IngestedJob]) -> Dict[str, object]:
    valid: List[IngestedJob] = []
    skipped = 0
    for job in jobs:
        company = _safe_text(job.company) or _extract_company_from_url(job.job_url)
        title = _safe_text(job.title)
        desc = _safe_text(job.job_description)
        url = _normalize_url(job.job_url)
        if not title or len(desc) < 40:
            skipped += 1
            continue
        valid.append(
            IngestedJob(
                company=company or "Unknown",
                title=title,
                location=_safe_text(job.location),
                job_url=url,
                source=_safe_text(job.source) or "Imported",
                job_description=desc,
                application_questions=_safe_text(job.application_questions),
                posted_at=job.posted_at,
            )
        )
    return {"jobs": valid, "skipped": skipped}
