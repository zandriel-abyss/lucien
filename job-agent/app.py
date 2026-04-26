from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from generators import GeneratorService, save_output
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
st.caption("Drafts high-quality application materials for manual review. Never auto-applies.")

if "generator" not in st.session_state:
    st.session_state["generator"] = GeneratorService()

if "active_job_id" not in st.session_state:
    st.session_state["active_job_id"] = None

if "generated_sections" not in st.session_state:
    st.session_state["generated_sections"] = {}



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



def render_dashboard() -> None:
    st.subheader("Dashboard")
    counts = status_counts()
    cols = st.columns(len(STATUSES))
    for idx, status in enumerate(STATUSES):
        cols[idx].metric(status, counts.get(status, 0))

    jobs = list_jobs()
    if not jobs:
        st.info("No jobs yet. Add one from the Add Job page.")
        return

    df = pd.DataFrame(jobs)

    c1, c2, c3 = st.columns(3)
    with c1:
        status_filter = st.multiselect("Filter by status", options=STATUSES)
    with c2:
        category_filter = st.multiselect(
            "Filter by category",
            options=sorted(df["category"].dropna().unique().tolist()) if "category" in df.columns else [],
        )
    with c3:
        recommendation_filter = st.multiselect(
            "Filter by recommendation",
            options=sorted(df["recommendation"].dropna().unique().tolist()) if "recommendation" in df.columns else [],
        )

    view = df.copy()
    if status_filter:
        view = view[view["status"].isin(status_filter)]
    if category_filter:
        view = view[view["category"].isin(category_filter)]
    if recommendation_filter:
        view = view[view["recommendation"].isin(recommendation_filter)]

    view = view.sort_values(by=["fit_score", "id"], ascending=[False, False])
    st.dataframe(
        view[
            [
                "id",
                "company",
                "title",
                "location",
                "category",
                "fit_score",
                "recommendation",
                "resume_mode",
                "status",
                "date_added",
            ]
        ],
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

        category = classify_role(job_description)
        fit = score_fit(title, location, job_description, category)

        payload = {
            "company": company,
            "title": title,
            "location": location,
            "job_url": job_url,
            "source": source,
            "job_description": job_description,
            "application_questions": questions,
            "category": category,
            "fit_score": fit.score,
            "recommendation": fit.recommendation,
            "resume_mode": fit.resume_mode,
            "status": "Saved",
            "follow_up_date": follow_up_date.isoformat() if follow_up_date else None,
            "recruiter_name": recruiter,
            "notes": notes,
            "generated_files": "",
        }

        job_id = add_job(payload)
        st.session_state["active_job_id"] = job_id

        st.success(f"Saved job #{job_id}.")
        st.markdown(f"**Category:** {category}")
        st.markdown(f"**Fit Score:** {fit.score} ({fit.recommendation})")
        st.markdown(f"**Suggested Resume Mode:** {fit.resume_mode}")
        st.markdown("**Top Strengths:**")
        for s in fit.strengths:
            st.write(f"- {s}")
        st.markdown("**Top Gaps:**")
        for g in fit.gaps:
            st.write(f"- {g}")



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
    st.write(f"**URL:** {job.get('job_url') or '-'}")
    st.write(f"**Category:** {job.get('category') or '-'}")
    st.write(f"**Fit Score:** {job.get('fit_score') or 0} ({job.get('recommendation') or 'N/A'})")
    st.write(f"**Recommended Resume Mode:** {job.get('resume_mode') or 'general'}")

    fit = score_fit(
        job.get("title") or "",
        job.get("location") or "",
        job.get("job_description") or "",
        job.get("category") or "General Leadership",
    )

    b1, b2 = st.columns(2)
    with b1:
        st.markdown("**Top 5 strengths**")
        for s in fit.strengths:
            st.write(f"- {s}")
    with b2:
        st.markdown("**Top 3 gaps**")
        for g in fit.gaps:
            st.write(f"- {g}")

    st.markdown("**Keywords to include**")
    st.write(", ".join(fit.keywords) if fit.keywords else "No high-signal keywords extracted.")

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
        update_job(
            job_id,
            {
                "status": new_status,
                "date_applied": applied_date.strip() or None,
                "follow_up_date": follow_up.strip() or None,
                "notes": notes,
            },
        )
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
        timeline_df = pd.DataFrame(timeline)[["created_at", "status", "note"]]
        st.dataframe(timeline_df, use_container_width=True)

    st.markdown("### Generate Draft Package")
    mode = st.selectbox(
        "Resume Strategy",
        options=list(RESUME_MODES.keys()),
        index=list(RESUME_MODES.keys()).index(job.get("resume_mode") or "general"),
        format_func=lambda k: RESUME_MODES[k]["label"],
    )

    if not st.session_state["generator"].api_available:
        st.warning("ANTHROPIC_API_KEY not found. Using mock generation output.")

    if st.button("Generate Role Strategy + Resume + Cover Letter + Answers + Interview Prep"):
        role_context = {
            "company": job["company"],
            "title": job["title"],
            "location": job.get("location"),
            "category": job.get("category"),
            "fit_score": job.get("fit_score"),
            "recommendation": job.get("recommendation"),
            "resume_mode": mode,
            "keywords": fit.keywords,
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
            },
        )
        add_timeline_note(job_id, "Drafted", "Generated new draft package")
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

    files = [line.strip() for line in (job.get("generated_files") or "").split("\n") if line.strip()]
    if files:
        st.markdown("### Saved Output Files")
        for f in files[::-1][:50]:
            st.write(f"- {f}")



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
    "Add Job": render_add_job,
    "Job Detail": render_job_detail,
    "Outputs": render_outputs,
    "Tracker Export": render_export,
    "Profile": render_profile,
}

selected_page = st.sidebar.radio("Pages", list(pages.keys()))
pages[selected_page]()
