# Job Agent (Semi-Automated Application Assistant)

A Streamlit app that helps a senior fintech/product leader prepare high-quality, role-specific application drafts.

This tool is **not** an auto-apply bot. It classifies roles, scores fit, suggests resume strategy, generates tailored draft materials, and logs everything in a tracker for manual review and submission.

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
  jobs.db
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

If `ANTHROPIC_API_KEY` is missing, the app still works with a built-in mock generator so you can test the flow.

## Features

### Core

1. Add job details (title/company/location/JD/questions/URL).
2. Auto-classify role category.
3. Auto-score fit (0-100) and recommendation.
4. Suggest resume mode (`general`, `regtech`, `hybrid`).
5. Generate tailored draft package:
   - role strategy
   - tailored resume content
   - cover letter
   - application answers
   - interview prep
6. Track status in SQLite (`Saved`, `Drafted`, `Applied`, `Interviewing`, `Rejected`, `Offer`, `Archived`).
7. Export tracker as CSV.

### Refinements

- **Role strategy output** for positioning Zack per role.
- **Interview prep output** including:
  - likely interview questions
  - 3 STAR stories to use
  - key metrics to mention
  - questions to ask interviewer
- **Editable generated outputs** in the Outputs page before saving/exporting.
- **Markdown exports** for:
  - resume version
  - cover letter
  - application answers
  - role strategy
  - interview prep
- **Status timeline notes** per job via a dedicated tracker timeline table.

## Sample Job Input

Use this sample in **Add Job**:

- Company: `Stripe`
- Title: `Senior Product Manager, Payments Risk Platform`
- Location: `Amsterdam, Netherlands`
- Job URL: `https://example.com/jobs/spm-payments-risk`
- Job Description (paste text):

```text
We are hiring a Senior Product Manager to lead our Payments Risk Platform.
You will own roadmap and strategy for fraud prevention, AML controls, and transaction monitoring.
You will partner with engineering, data science, and compliance teams to build scalable risk systems.
Experience with cross-border payments, regulatory controls, and analytics-driven decisioning is preferred.
```

- Application Questions (one per line):

```text
Why this role?
Describe a product impact you are proud of.
Describe your AML/KYC experience.
How do you work with engineering and compliance stakeholders?
```

## Notes

- The profile is stored as structured data in `profile.py` (no resume uploads needed).
- Generation logic is intentionally factual and constrained by provided profile data.
- Review all generated drafts before submitting any application.
