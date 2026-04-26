from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "jobs.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                job_url TEXT,
                source TEXT,
                job_description TEXT,
                application_questions TEXT,
                category TEXT,
                fit_score INTEGER,
                recommendation TEXT,
                resume_mode TEXT,
                status TEXT DEFAULT 'Saved',
                date_added TEXT,
                date_applied TEXT,
                follow_up_date TEXT,
                recruiter_name TEXT,
                notes TEXT,
                generated_files TEXT
            )
            """
        )


def add_job(payload: Dict[str, object]) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    payload = dict(payload)
    payload.setdefault("date_added", now)
    payload.setdefault("status", "Saved")

    fields = [
        "company",
        "title",
        "location",
        "job_url",
        "source",
        "job_description",
        "application_questions",
        "category",
        "fit_score",
        "recommendation",
        "resume_mode",
        "status",
        "date_added",
        "date_applied",
        "follow_up_date",
        "recruiter_name",
        "notes",
        "generated_files",
    ]

    values = [payload.get(f) for f in fields]

    with get_conn() as conn:
        cursor = conn.execute(
            f"INSERT INTO jobs ({', '.join(fields)}) VALUES ({', '.join(['?' for _ in fields])})",
            values,
        )
        return int(cursor.lastrowid)


def update_job(job_id: int, updates: Dict[str, object]) -> None:
    if not updates:
        return
    fields = list(updates.keys())
    values = [updates[k] for k in fields]
    set_clause = ", ".join([f"{f} = ?" for f in fields])

    with get_conn() as conn:
        conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE id = ?",
            values + [job_id],
        )


def get_job(job_id: int) -> Optional[Dict[str, object]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def list_jobs() -> List[Dict[str, object]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY COALESCE(fit_score, 0) DESC, id DESC").fetchall()
    return [dict(r) for r in rows]


def status_counts() -> Dict[str, int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS c FROM jobs GROUP BY status").fetchall()
    counts = {r["status"]: r["c"] for r in rows}
    for status in ["Saved", "Drafted", "Applied", "Interviewing", "Rejected", "Offer", "Archived"]:
        counts.setdefault(status, 0)
    return counts


def export_csv() -> pd.DataFrame:
    data = list_jobs()
    return pd.DataFrame(data)
