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
                generated_files TEXT,
                last_generation_mode TEXT,
                last_generation_error TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                status TEXT,
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS answer_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_type TEXT NOT NULL,
                question_text TEXT NOT NULL,
                answer_text TEXT NOT NULL,
                job_id INTEGER,
                quality_score INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
            """
        )
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
        }
        if "last_generation_mode" not in cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN last_generation_mode TEXT")
        if "last_generation_error" not in cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN last_generation_error TEXT")


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
        "last_generation_mode",
        "last_generation_error",
    ]

    values = [payload.get(f) for f in fields]

    with get_conn() as conn:
        cursor = conn.execute(
            f"INSERT INTO jobs ({', '.join(fields)}) VALUES ({', '.join(['?' for _ in fields])})",
            values,
        )
        job_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO job_timeline (job_id, status, note, created_at) VALUES (?, ?, ?, ?)",
            (job_id, payload.get("status", "Saved"), "Job added to tracker", now),
        )
        return job_id


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


def add_timeline_note(job_id: int, status: str, note: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO job_timeline (job_id, status, note, created_at) VALUES (?, ?, ?, ?)",
            (job_id, status, note, datetime.utcnow().isoformat(timespec="seconds")),
        )


def get_timeline(job_id: int) -> List[Dict[str, object]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, job_id, status, note, created_at FROM job_timeline WHERE job_id = ? ORDER BY id DESC",
            (job_id,),
        ).fetchall()
    return [dict(r) for r in rows]


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


def infer_question_type(question: str) -> str:
    q = (question or "").lower()
    if "why this company" in q or ("why" in q and "company" in q):
        return "why_company"
    if "why this role" in q or ("why" in q and "role" in q):
        return "why_role"
    if "impact" in q or "kpi" in q or "result" in q:
        return "impact"
    if "stakeholder" in q:
        return "stakeholder"
    if "leadership" in q or "team" in q:
        return "leadership"
    if "aml" in q or "kyc" in q or "compliance" in q:
        return "compliance"
    if "ai" in q or "ml" in q or "data" in q:
        return "ai_data"
    if "payment" in q or "treasury" in q:
        return "payments"
    return "general"


def add_answer_bank_entry(
    question_type: str,
    question_text: str,
    answer_text: str,
    job_id: int | None = None,
    quality_score: int | None = None,
) -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO answer_bank
            (question_type, question_text, answer_text, job_id, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                question_type,
                question_text.strip(),
                answer_text.strip(),
                job_id,
                quality_score,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        return int(cursor.lastrowid)


def get_answer_bank(question_type: str | None = None, limit: int = 20) -> List[Dict[str, object]]:
    with get_conn() as conn:
        if question_type:
            rows = conn.execute(
                """
                SELECT * FROM answer_bank
                WHERE question_type = ?
                ORDER BY COALESCE(quality_score, 0) DESC, id DESC
                LIMIT ?
                """,
                (question_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM answer_bank
                ORDER BY COALESCE(quality_score, 0) DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]
