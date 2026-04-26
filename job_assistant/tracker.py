from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .models import Job, JobStatus


class JobTracker:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    location TEXT NOT NULL,
                    job_url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    date_added TEXT NOT NULL,
                    job_description TEXT NOT NULL,
                    fit_score INTEGER,
                    fit_recommendation TEXT,
                    fit_explanation TEXT,
                    status TEXT NOT NULL DEFAULT 'saved',
                    follow_up_date TEXT,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )

    def add_job(self, job: Job) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO jobs (
                    company, title, location, job_url, source, date_added, job_description,
                    fit_score, fit_recommendation, fit_explanation, status, follow_up_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.company,
                    job.title,
                    job.location,
                    job.job_url,
                    job.source,
                    job.date_added,
                    job.job_description,
                    job.fit_score,
                    job.fit_recommendation,
                    job.fit_explanation,
                    job.status.value,
                    job.follow_up_date,
                    job.notes,
                ),
            )
            return int(cursor.lastrowid)

    def list_jobs(self) -> list[Job]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY date_added DESC, id DESC").fetchall()
        return [self._row_to_job(row) for row in rows]

    def get_job(self, job_id: int) -> Optional[Job]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def update_fit(self, job_id: int, score: int, recommendation: str, explanation: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET fit_score = ?, fit_recommendation = ?, fit_explanation = ?
                WHERE id = ?
                """,
                (score, recommendation, explanation, job_id),
            )

    def update_status_and_notes(
        self,
        job_id: int,
        status: JobStatus,
        follow_up_date: Optional[str],
        notes: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, follow_up_date = ?, notes = ?
                WHERE id = ?
                """,
                (status.value, follow_up_date, notes, job_id),
            )

    def export_csv(self, csv_path: Path) -> Path:
        jobs = self.list_jobs()
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "id",
                    "company",
                    "title",
                    "location",
                    "job_url",
                    "source",
                    "date_added",
                    "fit_score",
                    "fit_recommendation",
                    "status",
                    "follow_up_date",
                    "notes",
                ]
            )
            for job in jobs:
                writer.writerow(
                    [
                        job.id,
                        job.company,
                        job.title,
                        job.location,
                        job.job_url,
                        job.source,
                        job.date_added,
                        job.fit_score if job.fit_score is not None else "",
                        job.fit_recommendation or "",
                        job.status.value,
                        job.follow_up_date or "",
                        job.notes,
                    ]
                )
        return csv_path

    @staticmethod
    def count_by_status(jobs: Iterable[Job]) -> dict[str, int]:
        counts = {status.value: 0 for status in JobStatus}
        for job in jobs:
            counts[job.status.value] += 1
        return counts

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            company=row["company"],
            title=row["title"],
            location=row["location"],
            job_url=row["job_url"],
            source=row["source"],
            date_added=row["date_added"],
            job_description=row["job_description"],
            fit_score=row["fit_score"],
            fit_recommendation=row["fit_recommendation"],
            fit_explanation=row["fit_explanation"],
            status=JobStatus(row["status"]),
            follow_up_date=row["follow_up_date"],
            notes=row["notes"],
        )
