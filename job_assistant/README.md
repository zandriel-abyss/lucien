# Semi-Automated Job Application Assistant

This app helps a senior fintech/product leader:
- collect jobs,
- score fit,
- generate tailored drafts (resume, motivation letter, Q&A),
- and track pipeline status.

It **does not auto-submit** applications. All outputs are drafts for human review.

## Stack
- FastAPI + Jinja templates
- SQLite (`jobs.db`)
- Claude API via `ANTHROPIC_API_KEY`

## File Structure
- `app.py` - web app routes and UI actions
- `models.py` - data models and fit breakdown model
- `scoring.py` - hybrid fit scoring (deterministic 0-100 + optional Claude rationale)
- `resume_generator.py` - tailored resume + cover letter drafts
- `answer_generator.py` - application question answer drafts from STAR stories
- `intake.py` - URL-based job extraction and fallback parsing
- `tracker.py` - persistent tracker CRUD + CSV export
- `master_resume.md` - your canonical resume
- `profile.json` - your profile attributes
- `star_stories.md` - STAR answer source material
- `generated_outputs/` - generated resume/cover/answer files
- `jobs.db` - SQLite tracker DB (created at runtime)

## Setup
1. Install dependencies (from repo root):
   - `pip install -r requirements.txt`
2. Add your API key:
   - `export ANTHROPIC_API_KEY="your_key_here"`
3. Replace seed content in:
   - `job_assistant/master_resume.md`
   - `job_assistant/profile.json`
   - `job_assistant/star_stories.md`

## Run
From repo root:

```bash
uvicorn job_assistant.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Typical Workflow
1. Add jobs via URL fetch or manual paste on the dashboard.
2. Open the job detail page and run fit scoring.
3. Generate a tailored resume and inspect the master vs tailored diff.
4. Generate a role-specific motivation letter.
5. Paste application questions and draft concise STAR-based answers.
6. Update status/follow-up/notes in tracker.
7. Export tracker to CSV.

## Notes
- If `ANTHROPIC_API_KEY` is missing, generators write placeholder drafts with instructions.
- URL extraction attempts to infer title, description, company, and location from common page structures.
- Fit scoring always computes deterministic category scores, and appends an AI rationale when API access is available.
- Category scoring dimensions:
  - fintech/payments
  - AI/data
  - compliance/regtech
  - product leadership
  - seniority
  - location/visa
  - Dutch language requirement
