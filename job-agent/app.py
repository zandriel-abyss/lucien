from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from generators import GeneratorService, save_output
from ingestion import dedupe_jobs, filter_recent_jobs, parse_csv_jobs, parse_job_from_url, parse_rss_jobs
from optimizer import ats_coverage_report, build_apply_checklist
from profile import PROFILE, RESUME_MODES, STAR_STORIES
from scoring import classify_role, score_fit
from tracker import (
    add_job,
    add_timeline_note,
    export_csv,
    get_job,
    get_timeline,
    init_db,
    list_jobs,
    status_counts,
    update_job,
)

load_dotenv()
init_db()

STATUSES = ["Saved", "Drafted", "Applied", "Interviewing", "Rejected", "Offer", "Archived"]
SECTION_LABELS = {
    "role_strategy": "Role Strategy",
    "resume": "Tailored Resume",
    "cover_letter": "Cover Letter",
    "application_answers": "Application Answers",
    "interview_prep": "Interview Prep",
}
EXPORTABLE_SECTIONS = {
    "resume": "resume-version",
    "cover_letter": "cover-letter",
    "application_answers": "application-answers",
    "role_strategy": "role-strategy",
    "interview_prep": "interview-prep",
}

st.set_page_config(page_title="Job Agent", layout="wide")
st.title("Semi-Automated Job Application Assistant")
st.caption("Search, prioritize, and draft applications for manual submission. Never auto-applies.")

if "generator" not in st.session_state:
    st.session_state["generator"] = GeneratorService()

if "active_job_id" not in st.session_state:
    st.session_state["active_job_id"] = None

if "generated_sections" not in st.session_state:
    st.session_state["generated_sections"] = {}

if "ingested_jobs" not in st.session_state:
    st.session_state["ingested_jobs"] = []

mode_label = "Live API" if st.session_state["generator"].api_available else "Mock only"
st.info(f"Generation mode capability: {mode_label}")


def parse_questions(raw: str) -> List[str]:
    if not raw:
        return []
    parts = [p.strip(" -\t\n") for p in raw.split("\n")]
    return [p for p in parts if p]


def get_job_sections(job_id: int) -> Dict[str, str]:
    return st.session_state["generated_sections"].setdefault(job_id, {k: "" for k in SECTION_LABELS.keys()})


def append_generated_file(job: Dict[str, object], new_path: str) -> str:
    current = [line.strip() for line in (job.get("generated_files") or "").split("\n") if line.strip()]
    if new_path not in current:
        current.append(new_path)
    return "\n".join(current)


def _build_job_payload(company: str, title: str, location: str, job_url: str, source: str, jd: str, questions: str, recruiter: str = "", notes: str = "", follow_up_date: str | None = None) -> Dict[str, object]:
    category = classify_role(jd)
    fit = score_fit(title, location, jd, category)
    return {
        "company": company,
        "title": title,
        "location": location,
        "job_url": job_url,
        "source": source,
        "job_description": jd,
        "application_questions": questions,
        "category": category,
        "fit_score": fit.score,
        "recommendation": fit.recommendation,
        "resume_mode": fit.resume_mode,
        "status": "Saved",
        "follow_up_date": follow_up_date,
        "recruiter_name": recruiter,
        "notes": notes,
        "generated_files": "",
        "last_generation_mode": None,
        "last_generation_error": None,
    }


def render_dashboard() -> None:
    st.subheader("Dashboard")
    counts = status_counts()
    cols = st.columns(len(STATUSES))
    for idx, status in enumerate(STATUSES):
        cols[idx].metric(status, counts.get(status, 0))

    jobs = list_jobs()
    if not jobs:
        st.info("No jobs yet. Add one from Add Job or Ingestion pages.")
        return

    df = pd.DataFrame(jobs)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_filter = st.multiselect("Status", options=STATUSES)
    with c2:
        category_filter = st.multiselect("Category", options=sorted(df["category"].dropna().unique().tolist()) if "category" in df.columns else [])
    with c3:
        recommendation_filter = st.multiselect("Recommendation", options=sorted(df["recommendation"].dropna().unique().tolist()) if "recommendation" in df.columns else [])
    with c4:
        recency_window = st.selectbox("Posted within", options=["All", "24h", "3d", "7d"], index=0)

    view = df.copy()
    if status_filter:
        view = view[view["status"].isin(status_filter)]
    if category_filter:
        view = view[view["category"].isin(category_filter)]
    if recommendation_filter:
        view = view[view["recommendation"].isin(recommendation_filter)]

    if recency_window != "All" and "date_added" in view.columns:
        cutoff_days = {"24h": 1, "3d": 3, "7d": 7}[recency_window]
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=cutoff_days)
        parsed = pd.to_datetime(view["date_added"], errors="coerce", utc=True)
        view = view[parsed >= cutoff]

    view = view.sort_values(by=["fit_score", "id"], ascending=[False, False])
    st.dataframe(
        view[["id", "company", "title", "location", "source", "category", "fit_score", "recommendation", "resume_mode", "last_generation_mode", "status", "date_added"]],
        use_container_width=True,
    )


def render_add_job() -> None:
    st.subheader("Add Job")

    with st.form("add_job_form"):
        c1, c2 = st.columns(2)
        with c1:
            company = st.text_input("Company")
            title = st.text_input("Job Title")
            location = st.text_input("Location")
            job_url = st.text_input("Job URL")
        with c2:
            source = st.text_input("Source", value="Manual")
            recruiter = st.text_input("Recruiter Name (optional)")
            follow_up_date = st.date_input("Follow-up Date", value=None)

        job_description = st.text_area("Job Description", height=240)
        questions = st.text_area("Application Questions (one per line)", height=120)
        notes = st.text_area("Notes", height=90)

        submitted = st.form_submit_button("Classify, Score, and Save")

    if submitted:
        if not company or not title or not job_description:
            st.error("Company, title, and job description are required.")
            return

        payload = _build_job_payload(
            company=company,
            title=title,
            location=location,
            job_url=job_url,
            source=source,
            jd=job_description,
            questions=questions,
            recruiter=recruiter,
            notes=notes,
            follow_up_date=follow_up_date.isoformat() if follow_up_date else None,
        )
        job_id = add_job(payload)
        st.session_state["active_job_id"] = job_id
        st.success(f"Saved job #{job_id}.")


def render_ingestion() -> None:
    st.subheader("Ingestion (CSV / RSS / Career URL)")
    st.caption("Use user-triggered imports only. Avoid automated login scraping and never auto-apply.")

    tab1, tab2, tab3 = st.tabs(["CSV Import", "RSS Feed", "Career URL"])

    with tab1:
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        st.caption("Expected columns: company,title,location,job_url,job_description,application_questions,posted_at")
        if uploaded is not None:
            content = uploaded.read().decode("utf-8", errors="ignore")
            jobs = parse_csv_jobs(content)
            window = st.selectbox("Recency filter", options=["24h", "3d", "7d"], key="csv-window")
            jobs = filter_recent_jobs(jobs, window)
            jobs = dedupe_jobs(jobs, list_jobs())
            st.session_state["ingested_jobs"] = jobs
            st.success(f"Parsed {len(jobs)} new jobs after dedupe/filter.")

    with tab2:
        rss_url = st.text_input("RSS Feed URL", key="rss-url")
        window = st.selectbox("Recency filter", options=["24h", "3d", "7d"], key="rss-window")
        if st.button("Fetch RSS Jobs"):
            try:
                jobs = parse_rss_jobs(rss_url, source="RSS")
                jobs = filter_recent_jobs(jobs, window)
                jobs = dedupe_jobs(jobs, list_jobs())
                st.session_state["ingested_jobs"] = jobs
                st.success(f"Fetched {len(jobs)} new jobs.")
            except Exception as exc:
                st.error(str(exc))

    with tab3:
        url = st.text_input("Company career/job URL", key="career-url")
        if st.button("Parse URL"):
            try:
                job = parse_job_from_url(url)
                jobs = dedupe_jobs([job], list_jobs())
                st.session_state["ingested_jobs"] = jobs
                st.success(f"Parsed {len(jobs)} new jobs.")
            except Exception as exc:
                st.error(str(exc))

    jobs = st.session_state.get("ingested_jobs", [])
    if jobs:
        st.markdown("### Preview & Save to Tracker")
        preview = pd.DataFrame([j.__dict__ for j in jobs])
        st.dataframe(preview, use_container_width=True)

        if st.button("Save All Previewed Jobs"):
            saved = 0
            for job in jobs:
                if not job.company or not job.title or not job.job_description:
                    continue
                payload = _build_job_payload(
                    company=job.company,
                    title=job.title,
                    location=job.location,
                    job_url=job.job_url,
                    source=job.source,
                    jd=job.job_description,
                    questions=job.application_questions,
                )
                add_job(payload)
                saved += 1
            st.success(f"Saved {saved} jobs to tracker.")
            st.session_state["ingested_jobs"] = []


def render_job_detail() -> None:
    st.subheader("Job Detail")

    jobs = list_jobs()
    if not jobs:
        st.info("No jobs available. Add one first.")
        return

    job_options = {f"#{j['id']} - {j['company']} - {j['title']}": j["id"] for j in jobs}
    default_idx = 0
    if st.session_state.get("active_job_id"):
        for idx, (_, jid) in enumerate(job_options.items()):
            if jid == st.session_state["active_job_id"]:
                default_idx = idx
                break

    selected_label = st.selectbox("Select a job", options=list(job_options.keys()), index=default_idx)
    job_id = job_options[selected_label]
    st.session_state["active_job_id"] = job_id

    job = get_job(job_id)
    if not job:
        st.warning("Job not found.")
        return

    sections = get_job_sections(job_id)

    st.markdown(f"### {job['title']} @ {job['company']}")
    st.write(f"**Location:** {job.get('location') or '-'}")
    st.write(f"**Source:** {job.get('source') or '-'}")
    st.write(f"**URL:** {job.get('job_url') or '-'}")
    st.write(f"**Category:** {job.get('category') or '-'}")
    st.write(f"**Fit Score:** {job.get('fit_score') or 0} ({job.get('recommendation') or 'N/A'})")
    st.write(f"**Recommended Resume Mode:** {job.get('resume_mode') or 'general'}")
    st.write(f"**Last generation mode:** {job.get('last_generation_mode') or 'not-run'}")
    if job.get("last_generation_error"):
        st.warning(f"Last generation warning: {job['last_generation_error']}")

    fit = score_fit(job.get("title") or "", job.get("location") or "", job.get("job_description") or "", job.get("category") or "General Leadership")
    ats = ats_coverage_report(job.get("job_description") or "")

    b1, b2 = st.columns(2)
    with b1:
        st.markdown("**Top Strengths**")
        for s in fit.strengths:
            st.write(f"- {s}")
    with b2:
        st.markdown("**Top Gaps**")
        for g in fit.gaps:
            st.write(f"- {g}")

    st.markdown("### ATS Keyword Coverage")
    c1, c2, c3 = st.columns(3)
    c1.metric("Coverage", f"{ats['coverage_percent']}%")
    c2.metric("Matched keywords", len(ats["matched_keywords"]))
    c3.metric("Missing keywords", len(ats["missing_keywords"]))

    st.write("**Keywords to include:**", ", ".join(ats["jd_keywords"][:20]) or "-")
    if ats["suggestions"]:
        st.write("**Optimization suggestions:**")
        for line in ats["suggestions"]:
            st.write(f"- {line}")

    with st.expander("Job Description"):
        st.write(job.get("job_description") or "")

    st.markdown("### Update Tracking")
    c1, c2, c3 = st.columns(3)
    new_status = c1.selectbox("Status", options=STATUSES, index=STATUSES.index(job.get("status", "Saved")))
    applied_date = c2.text_input("Date Applied (YYYY-MM-DD)", value=job.get("date_applied") or "")
    follow_up = c3.text_input("Follow-up Date (YYYY-MM-DD)", value=job.get("follow_up_date") or "")
    notes = st.text_area("Notes", value=job.get("notes") or "", height=90)

    if st.button("Save Job Updates"):
        changed_status = new_status != (job.get("status") or "Saved")
        update_job(job_id, {"status": new_status, "date_applied": applied_date.strip() or None, "follow_up_date": follow_up.strip() or None, "notes": notes})
        if changed_status:
            add_timeline_note(job_id, new_status, f"Status changed to {new_status}")
        st.success("Job updated.")

    st.markdown("### Status Timeline Notes")
    t1, t2 = st.columns([1, 3])
    timeline_status = t1.selectbox("Timeline status", options=STATUSES, index=STATUSES.index(job.get("status") or "Saved"), key=f"timeline-status-{job_id}")
    timeline_note = t2.text_input("Timeline note", key=f"timeline-note-{job_id}")
    if st.button("Add Timeline Note", key=f"timeline-add-{job_id}"):
        if timeline_note.strip():
            add_timeline_note(job_id, timeline_status, timeline_note.strip())
            st.success("Timeline note added.")
        else:
            st.warning("Enter a note before adding.")

    timeline = get_timeline(job_id)
    if timeline:
        st.dataframe(pd.DataFrame(timeline)[["created_at", "status", "note"]], use_container_width=True)

    st.markdown("### Generate Draft Package")
    mode = st.selectbox("Resume Strategy", options=list(RESUME_MODES.keys()), index=list(RESUME_MODES.keys()).index(job.get("resume_mode") or "general"), format_func=lambda k: RESUME_MODES[k]["label"])

    if not st.session_state["generator"].api_available:
        st.warning("ANTHROPIC_API_KEY not found. Using mock generation output.")

    if st.button("Generate Draft Package"):
        role_context = {
            "company": job["company"],
            "title": job["title"],
            "location": job.get("location"),
            "category": job.get("category"),
            "fit_score": job.get("fit_score"),
            "recommendation": job.get("recommendation"),
            "resume_mode": mode,
            "keywords": ats["jd_keywords"][:15],
            "strengths": fit.strengths,
            "gaps": fit.gaps,
            "job_description": job.get("job_description"),
        }
        questions = parse_questions(job.get("application_questions") or "")
        with st.spinner("Generating package..."):
            sections = st.session_state["generator"].generate_package(role_context, mode, questions)

        st.session_state["generated_sections"][job_id] = sections
        update_job(
            job_id,
            {
                "resume_mode": mode,
                "status": "Drafted" if job.get("status") == "Saved" else job.get("status"),
                "last_generation_mode": st.session_state["generator"].last_generation_mode,
                "last_generation_error": st.session_state["generator"].last_generation_error or None,
            },
        )
        add_timeline_note(job_id, "Drafted", "Generated new draft package")
        if st.session_state["generator"].last_generation_mode == "mock":
            st.warning("Generation used mock fallback. Check API key/configuration for live output.")
        st.success("Generated draft sections. Review and export from Outputs page.")


def render_outputs() -> None:
    st.subheader("Outputs")
    jobs = list_jobs()
    if not jobs:
        st.info("No jobs yet.")
        return

    job_options = {f"#{j['id']} - {j['company']} - {j['title']}": j["id"] for j in jobs}
    default_idx = 0
    if st.session_state.get("active_job_id"):
        for idx, (_, jid) in enumerate(job_options.items()):
            if jid == st.session_state["active_job_id"]:
                default_idx = idx
                break

    selected_label = st.selectbox("Select job for output review", options=list(job_options.keys()), index=default_idx)
    job_id = job_options[selected_label]
    st.session_state["active_job_id"] = job_id
    job = get_job(job_id)
    sections = get_job_sections(job_id)

    if not any(v.strip() for v in sections.values()):
        st.info("No generated sections in this session yet. Go to Job Detail and generate drafts first.")

    for key, label in SECTION_LABELS.items():
        sections[key] = st.text_area(label, value=sections.get(key, ""), height=220, key=f"output-edit-{job_id}-{key}")

    c1, c2 = st.columns(2)
    if c1.button("Save Edited Sections (Session)"):
        st.session_state["generated_sections"][job_id] = sections
        st.success("Edits saved in session state.")

    if c2.button("Export All Sections as Markdown Files"):
        saved = []
        for section_key, slug in EXPORTABLE_SECTIONS.items():
            if sections.get(section_key, "").strip():
                path = save_output(job["company"], job["title"], sections[section_key], slug)
                saved.append(path)
                job["generated_files"] = append_generated_file(job, path)
        if saved:
            update_job(job_id, {"generated_files": job.get("generated_files", "")})
            add_timeline_note(job_id, job.get("status") or "Drafted", "Exported all output markdown files")
            st.success(f"Exported {len(saved)} files.")
        else:
            st.warning("Nothing to export yet.")

    st.markdown("### Individual Markdown Exports")
    export_cols = st.columns(len(EXPORTABLE_SECTIONS))
    for idx, (section_key, slug) in enumerate(EXPORTABLE_SECTIONS.items()):
        if export_cols[idx].button(f"Export {SECTION_LABELS[section_key]}"):
            content = sections.get(section_key, "").strip()
            if not content:
                st.warning(f"{SECTION_LABELS[section_key]} is empty.")
                continue
            path = save_output(job["company"], job["title"], content, slug)
            merged = append_generated_file(job, path)
            update_job(job_id, {"generated_files": merged})
            job["generated_files"] = merged
            add_timeline_note(job_id, job.get("status") or "Drafted", f"Exported {SECTION_LABELS[section_key]} markdown")
            st.success(f"Saved {SECTION_LABELS[section_key]} to {path}")


def render_apply_assistant() -> None:
    st.subheader("Apply Assistant")
    st.caption("Supports LinkedIn Easy Apply / company portals with manual final submit.")

    jobs = list_jobs()
    if not jobs:
        st.info("No jobs available.")
        return

    job_options = {f"#{j['id']} - {j['company']} - {j['title']}": j["id"] for j in jobs}
    selected_label = st.selectbox("Select job", options=list(job_options.keys()))
    job = get_job(job_options[selected_label])
    sections = get_job_sections(job["id"])

    checklist = build_apply_checklist(job["company"], job["title"], job.get("job_url") or "")
    st.markdown("### Manual Application Checklist")
    for item in checklist:
        st.write(f"- {item}")

    st.markdown("### Portal-Specific Questions")
    portal_questions = st.text_area("Paste additional portal questions", height=150)
    if st.button("Generate Additional Answers"):
        role_context = {
            "company": job["company"],
            "title": job["title"],
            "location": job.get("location"),
            "category": job.get("category"),
            "fit_score": job.get("fit_score"),
            "recommendation": job.get("recommendation"),
            "resume_mode": job.get("resume_mode") or "general",
            "keywords": ats_coverage_report(job.get("job_description") or "")["jd_keywords"][:15],
            "strengths": score_fit(job.get("title") or "", job.get("location") or "", job.get("job_description") or "", job.get("category") or "General Leadership").strengths,
            "gaps": score_fit(job.get("title") or "", job.get("location") or "", job.get("job_description") or "", job.get("category") or "General Leadership").gaps,
            "job_description": job.get("job_description"),
        }
        extra_questions = parse_questions(portal_questions)
        if not extra_questions:
            st.warning("Please paste at least one question.")
        else:
            out = st.session_state["generator"].generate_package(role_context, job.get("resume_mode") or "general", extra_questions)
            existing_answers = sections.get("application_answers", "")
            sections["application_answers"] = (existing_answers + "\n\n" + out.get("application_answers", "")).strip()
            st.session_state["generated_sections"][job["id"]] = sections
            update_job(
                job["id"],
                {
                    "last_generation_mode": st.session_state["generator"].last_generation_mode,
                    "last_generation_error": st.session_state["generator"].last_generation_error or None,
                },
            )
            add_timeline_note(job["id"], job.get("status") or "Drafted", "Generated additional portal question answers")
            if st.session_state["generator"].last_generation_mode == "mock":
                st.warning("Additional answers used mock fallback due to API error/configuration.")
            st.success("Additional answers appended to Application Answers section.")

    if st.button("Mark as Applied Now"):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        update_job(job["id"], {"status": "Applied", "date_applied": today})
        add_timeline_note(job["id"], "Applied", "Manually submitted application")
        st.success("Status updated to Applied.")


def render_export() -> None:
    st.subheader("Tracker Export")
    df = export_csv()
    if df.empty:
        st.info("No jobs to export yet.")
        return

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download jobs CSV",
        data=csv_data,
        file_name=f"job-tracker-{datetime.utcnow().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
    st.dataframe(df, use_container_width=True)


def render_profile() -> None:
    st.subheader("Profile Snapshot")
    st.write(f"**Name:** {PROFILE['personal']['name']} ({PROFILE['personal']['preferred_name']})")
    st.write(f"**Location:** {PROFILE['personal']['location']}")
    st.write(f"**Experience:** {PROFILE['personal']['experience_years']} years")
    st.write("**Target Positioning:**")
    for item in PROFILE["personal"]["positioning"]:
        st.write(f"- {item}")

    st.write("**STAR Stories Available for Application Answers:**")
    for story in STAR_STORIES:
        st.write(f"- {story['title']}")


pages = {
    "Dashboard": render_dashboard,
    "Ingestion": render_ingestion,
    "Add Job": render_add_job,
    "Job Detail": render_job_detail,
    "Outputs": render_outputs,
    "Apply Assistant": render_apply_assistant,
    "Tracker Export": render_export,
    "Profile": render_profile,
}

selected_page = st.sidebar.radio("Pages", list(pages.keys()))
pages[selected_page]()
