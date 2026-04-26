# Job Agent (Semi-Automated Application Assistant)

A Streamlit app that helps a senior fintech/product leader search, prioritize, and prepare high-quality, role-specific application drafts.

This tool is **not** a blind auto-apply bot. It prepares strong materials for manual review and submission.

## Stack

- Python
- Streamlit
- SQLite
- Anthropic Claude API (`ANTHROPIC_API_KEY`)
- Modular code architecture

## Project Structure

```text
job-agent/
  app.py
  profile.py
  scoring.py
  generators.py
  tracker.py
  prompts.py
  ingestion.py
  optimizer.py
  outputs/
  requirements.txt
  README.md
```

## Setup

1. Create a virtual environment:
   - macOS/Linux: `python -m venv .venv`
   - Windows (PowerShell): `python -m venv .venv`
2. Activate it:
   - macOS/Linux: `source .venv/bin/activate`
   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` in `job-agent/` and set:
   - `ANTHROPIC_API_KEY=your_key_here`
5. Run app:
   - `streamlit run app.py`

If `ANTHROPIC_API_KEY` is missing, the app still works with a built-in mock generator.

## V2 Features

### Search Ingestion (safe)

- CSV job import
- RSS feed ingestion
- Manual career page URL parsing
- Recency filters (`24h`, `3d`, `7d`)
- Dedupe against tracker by `company + title + job_url`

### Triage & Drafting

- Role classification and fit scoring
- Resume strategy recommendation
- Role strategy generation
- Tailored resume content
- Cover letter generation
- Application answers generation
- Interview prep generation

### Optimization

- JD keyword extraction
- ATS coverage report
- Missing keyword suggestions for factual tailoring

### Apply Assistant (manual final submit)

- LinkedIn/company portal checklist
- Additional portal question answering
- Status update to `Applied` after manual submit

## Guardrails

- Never auto-apply.
- Never bypass login.
- Never claim experience/metrics not in profile data.
- Keep all outputs factual and review before submission.
