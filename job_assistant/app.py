from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .answer_generator import ApplicationAnswerGenerator
from .intake import JobIntakeService
from .models import Job, JobStatus, utc_now_iso
from .resume_generator import CoverLetterGenerator, ResumeGenerator
from .scoring import FitScorer
from .tracker import JobTracker
import difflib


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR
OUTPUT_DIR = DATA_DIR / "generated_outputs"
DB_PATH = DATA_DIR / "jobs.db"
MASTER_RESUME = DATA_DIR / "master_resume.md"
PROFILE_PATH = DATA_DIR / "profile.json"
STAR_STORIES = DATA_DIR / "star_stories.md"

app = FastAPI(title="Job Application Assistant")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

tracker = JobTracker(DB_PATH)
scorer = FitScorer(PROFILE_PATH)
resume_gen = ResumeGenerator(MASTER_RESUME, PROFILE_PATH, OUTPUT_DIR)
cover_gen = CoverLetterGenerator(MASTER_RESUME, PROFILE_PATH, OUTPUT_DIR)
answer_gen = ApplicationAnswerGenerator(PROFILE_PATH, STAR_STORIES, OUTPUT_DIR)
intake = JobIntakeService()


@app.get("/")
def dashboard(request: Request):
    jobs = tracker.list_jobs()
    status_counts = tracker.count_by_status(jobs)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "jobs": jobs, "status_counts": status_counts},
    )


@app.post("/jobs/add")
def add_job(
    company: str = Form(...),
    title: str = Form(...),
    location: str = Form(""),
    job_url: str = Form(""),
    source: str = Form("manual"),
    job_description: str = Form(""),
):
    job = Job(
        id=None,
        company=company.strip(),
        title=title.strip(),
        location=location.strip(),
        job_url=job_url.strip(),
        source=source.strip() or "manual",
        date_added=utc_now_iso(),
        job_description=job_description.strip(),
    )
    job_id = tracker.add_job(job)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/add-from-url")
def add_job_from_url(
    job_url: str = Form(...),
    source: str = Form("web"),
):
    try:
        intake_result = intake.fetch_from_url(job_url.strip(), source=source.strip() or "web")
    except Exception:
        # Fall back to a minimal entry if extraction fails.
        intake_result = None

    job = Job(
        id=None,
        company=(intake_result.company if intake_result else "Unknown Company"),
        title=(intake_result.title if intake_result else "Unknown Role"),
        location=(intake_result.location if intake_result else "Unknown"),
        job_url=job_url.strip(),
        source=(intake_result.source if intake_result else source.strip() or "web"),
        date_added=utc_now_iso(),
        job_description=(intake_result.description if intake_result else ""),
    )
    job_id = tracker.add_job(job)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.get("/jobs/{job_id}")
def job_detail(request: Request, job_id: int):
    job = tracker.get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        "job_detail.html",
        {
            "request": request,
            "job": job,
            "statuses": [s.value for s in JobStatus],
        },
    )


@app.post("/jobs/{job_id}/score")
def score_job(job_id: int):
    job = tracker.get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)

    fit = scorer.score_with_rationale(job.job_description, job.location)
    tracker.update_fit(job_id, fit.overall_score, fit.recommendation, fit.explanation)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/resume")
def generate_resume(job_id: int):
    job = tracker.get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)
    resume_gen.generate_tailored_resume(job)
    tracker.update_status_and_notes(
        job_id=job_id,
        status=JobStatus.DRAFTED,
        follow_up_date=job.follow_up_date,
        notes=job.notes,
    )
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.get("/jobs/{job_id}/resume-diff", response_class=HTMLResponse)
def resume_diff(request: Request, job_id: int):
    job = tracker.get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)

    candidate_name = f"{resume_gen._slug(job.company)}_{resume_gen._slug(job.title)}_resume.md"
    tailored_path = OUTPUT_DIR / candidate_name
    if not tailored_path.exists():
        return HTMLResponse(
            "<h3>No tailored resume found yet.</h3><p>Generate one first from the job page.</p>",
            status_code=404,
        )

    master_text = MASTER_RESUME.read_text(encoding="utf-8").splitlines()
    tailored_text = tailored_path.read_text(encoding="utf-8").splitlines()
    html_table = difflib.HtmlDiff(wrapcolumn=90).make_table(
        master_text,
        tailored_text,
        fromdesc="Master Resume",
        todesc="Tailored Resume",
        context=True,
        numlines=2,
    )
    return templates.TemplateResponse(
        "resume_diff.html",
        {"request": request, "job": job, "diff_table": html_table},
    )


@app.post("/jobs/{job_id}/cover-letter")
def generate_cover_letter(job_id: int):
    job = tracker.get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)
    cover_gen.generate_cover_letter(job)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/answers")
def generate_answers(job_id: int, questions: str = Form(...)):
    job = tracker.get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)
    answer_gen.generate_answers(job, questions)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/update")
def update_job(
    job_id: int,
    status: str = Form(...),
    follow_up_date: Optional[str] = Form(None),
    notes: str = Form(""),
):
    job = tracker.get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)

    tracker.update_status_and_notes(
        job_id=job_id,
        status=JobStatus(status),
        follow_up_date=follow_up_date or None,
        notes=notes.strip(),
    )
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.get("/export.csv")
def export_csv():
    csv_path = tracker.export_csv(OUTPUT_DIR / "job_tracker_export.csv")
    return FileResponse(path=csv_path, media_type="text/csv", filename=csv_path.name)
