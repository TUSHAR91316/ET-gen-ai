import uuid
import streamlit as st
import json
from typing import List

from enterprise_content_ops import (
    CHANNELS_DEFAULT,
    DEFAULT_GUARDRAILS,
    DEFAULT_LANGUAGES,
    ContentOpsWorkflow,
    ContentRequest,
)


st.set_page_config(page_title="Enterprise Content Ops Agent", page_icon="🧠", layout="wide")

st.markdown(
    """
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .panel {
        background-color: #171a22;
        border: 1px solid rgba(255,255,255,0.08);
        padding: 16px;
        border-radius: 10px;
    }
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #22c55e;
    }
</style>
""",
    unsafe_allow_html=True,
)


def _init_session() -> None:
    if "job_id" not in st.session_state:
        st.session_state.job_id = f"job_{uuid.uuid4().hex[:12]}"
    if "preview" not in st.session_state:
        st.session_state.preview = None  # dict with drafted_assets, compliance_report
    if "run" not in st.session_state:
        st.session_state.run = None


def _render_findings(findings: List) -> None:
    if not findings:
        st.success("No compliance issues found.")
        return
    for f in findings:
        sev_color = "#ef4444" if f.severity == "high" else ("#f59e0b" if f.severity == "med" else "#22c55e")
        st.markdown(
            f"""
            <div class="panel" style="border-color: rgba(255,255,255,0.12); background-color: rgba(255,255,255,0.03);">
            <div style="color: {sev_color}; font-weight: 700;">[{f.severity.upper()}] {f.rule_id}</div>
            <div style="margin-top: 6px;">{f.message}</div>
            """
            + (f"<div style='margin-top: 6px; color:#cbd5e1'>Evidence: {f.evidence}</div>" if f.evidence else "")
            + (f"<div style='margin-top: 6px; color:#cbd5e1'>Suggested fix: {f.suggested_fix}</div>" if f.suggested_fix else "")
            + "</div>",
            unsafe_allow_html=True,
        )


def main() -> None:
    _init_session()
    st.title("Enterprise Content Lifecycle Agent")
    st.caption("Multi-agent pipeline: Draft -> Compliance Guardrails -> Human Approval -> Localization -> Packaging -> Publish Calendar")

    wf = ContentOpsWorkflow(output_dir="runs")

    # Sidebar controls
    with st.sidebar:
        st.subheader("Inputs")
        spec = st.text_area(
            "Content spec / internal notes",
            "Launch a new product update page and social posts.\nInclude brand-safe language and required disclaimers.\nLocalize for Indian audiences.",
            height=160,
        )
        audience = st.text_input("Target audience", "enterprise content managers and brand/legal teams")

        st.markdown("### Channels")
        selected_channels = st.multiselect("Choose channels", options=CHANNELS_DEFAULT, default=CHANNELS_DEFAULT[:2])

        st.markdown("### Languages")
        selected_languages = st.multiselect("Choose languages", options=DEFAULT_LANGUAGES, default=DEFAULT_LANGUAGES[:2])

        compliance_threshold = st.slider("Compliance threshold", min_value=0.6, max_value=0.98, value=0.85, step=0.01)
        st.divider()
        if st.button("Generate Draft + Compliance Report", type="primary"):
            st.session_state.preview = None
            st.session_state.run = None
            st.session_state.job_id = f"job_{uuid.uuid4().hex[:12]}"

            if not selected_channels:
                st.error("Please select at least one channel.")
                return
            if not selected_languages:
                st.error("Please select at least one language.")
                return

            request = ContentRequest(
                spec=spec,
                audience=audience,
                channels=selected_channels,
                languages=selected_languages,
                guardrails=DEFAULT_GUARDRAILS,
                job_id=st.session_state.job_id,
            )

            with st.spinner("Drafting + checking compliance (pre-approval gate)..."):
                drafted_assets, compliance_report, strategy = wf.preview_draft_and_compliance(request, compliance_threshold=compliance_threshold)

            st.session_state.preview = {
                "request": request,
                "drafted_assets": drafted_assets,
                "compliance_report": compliance_report,
                "strategy": strategy,
            }

    # Main content
    preview = st.session_state.preview
    if not preview:
        st.markdown("## Demo flow")
        st.markdown(
            """
1. Generate a draft per channel.
2. Run compliance guardrails and show an audit-style report.
3. Approve in the UI (human-in-the-loop).
4. Run localization and packaging to produce publish-ready payloads.
"""
        )
        return

    compliance_report = preview["compliance_report"]
    drafted_assets = preview["drafted_assets"]
    request = preview["request"]

    st.markdown("## Compliance Gate (Human Approval)")
    colA, colB = st.columns([1, 1])
    with colA:
        st.metric("Compliance score", f"{compliance_report.overall_score}")
        st.metric("Passed", str(compliance_report.passed))
        st.caption(f"Threshold used: {compliance_report.threshold}")

    with colB:
        st.subheader("Findings")
        _render_findings(compliance_report.findings)

    st.divider()

    st.markdown("## Draft Preview")
    # Show drafts grouped by channel.
    tabs = st.tabs([f"{a.channel}" for a in drafted_assets] or ["draft"])
    # Build a unique tab per channel by default.
    channels = sorted({a.channel for a in drafted_assets})
    tabs = st.tabs(channels)
    for i, channel in enumerate(channels):
        with tabs[i]:
            channel_assets = [a for a in drafted_assets if a.channel == channel]
            for a in channel_assets:
                st.markdown(f"### {a.variant_id}: {a.title}")
                st.code(a.body[:900] + ("..." if len(a.body) > 900 else ""), language="text")
                st.divider()

    st.divider()

    st.markdown("## Approval and Publishing")
    decision = st.radio("Approval decision", options=["Approve", "Request edits"], horizontal=True, index=0)
    human_feedback = ""
    if decision == "Request edits":
        human_feedback = st.text_area("Edit notes (appended to spec for re-draft)", placeholder="e.g., use softer claims, ensure more disclaimers, adjust CTA tone.", height=90)

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Run Full Workflow (after approval)", type="primary"):
            # If rejected, rerun the preview with human feedback (single loop for demo).
            if decision != "Approve":
                if not human_feedback.strip():
                    st.warning("Provide edit notes or choose Approve.")
                    return
                request2 = ContentRequest(
                    spec=request.spec + "\n\nHUMAN_FEEDBACK: " + human_feedback.strip(),
                    audience=request.audience,
                    channels=request.channels,
                    languages=request.languages,
                    guardrails=request.guardrails,
                    job_id=st.session_state.job_id,
                )
                with st.spinner("Regenerating draft + compliance..."):
                    drafted_assets2, compliance_report2, strategy2 = wf.preview_draft_and_compliance(
                        request2, compliance_threshold=compliance_threshold
                    )
                st.session_state.preview = {
                    "request": request2,
                    "drafted_assets": drafted_assets2,
                    "compliance_report": compliance_report2,
                    "strategy": strategy2,
                }
                return

            # Human approved. Run the full pipeline with the internal gate automatically returning approved.
            run = None
            with st.spinner("Running localization + packaging..."):
                run = wf.run(
                    request,
                    approval_callback=lambda _draft_payload, _report: {"approved": True, "mode": "manual_ui_approved"},
                    auto_approve=False,
                    compliance_threshold=compliance_threshold,
                )
            st.session_state.run = run

    with c2:
        if st.session_state.run:
            run = st.session_state.run
            st.markdown("### Publish Calendar (Demo)")
            batches = run.packaged.publish_batches if run.packaged else []
            for b in batches:
                st.info(f"{b['scheduled_at']} | {b['channel']} ({b['language']}) | {b['utm_campaign']}")
                with st.expander("View payload"):
                    st.json(b)

            if run.estimated_impact:
                st.markdown("### Impact Model (Back-of-envelope)")
                st.json(run.estimated_impact)
        else:
            st.info("Approve above and click `Run Full Workflow` to generate localized + packaged outputs.")


if __name__ == "__main__":
    main()
