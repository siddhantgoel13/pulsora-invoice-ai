import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.extractor import extract_text_and_pages
from src.llm_parser import parse_invoice
from src.models import InvoiceData
from src.validator import validate_invoice

st.set_page_config(
    page_title="Pulsora — Utility Invoice Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# UI ONLY — extraction / parsing / validation logic is unchanged
# ============================================================
st.markdown(
    """
<style>
/* ---------- Global ---------- */
:root {
    --navy: #0b2d5c;
    --navy-2: #123f78;
    --blue: #1677e8;
    --blue-2: #2f8cff;
    --blue-soft: #eef6ff;
    --border: #d7e3f0;
    --text: #12233f;
    --muted: #5e718b;
    --green: #168447;
    --green-soft: #ecf9f1;
    --amber: #b86b00;
    --amber-soft: #fff7e6;
}

.stApp {
    background: linear-gradient(180deg, #f5f9fe 0%, #ffffff 42%, #f7fbff 100%);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1540px;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #092b59 0%, #0d3973 100%);
    border-right: 1px solid #123f78;
}

section[data-testid="stSidebar"] > div {
    padding-top: 2rem;
}

section[data-testid="stSidebar"] * {
    color: #f5f9ff !important;
}

.sidebar-brand {
    font-size: 2rem;
    font-weight: 850;
    letter-spacing: -0.04em;
    line-height: 1.05;
    margin-bottom: 0.25rem;
}

.sidebar-sub {
    font-size: 0.98rem;
    color: #c9ddf6 !important;
    margin-bottom: 1.5rem;
}

.sidebar-line {
    height: 1px;
    background: rgba(255,255,255,.22);
    margin: 1.2rem 0 1.5rem;
}

.workflow-item {
    padding: 0.8rem 0.9rem;
    border-radius: 12px;
    margin-bottom: 0.45rem;
    background: rgba(255,255,255,.045);
}

.workflow-item.active {
    background: linear-gradient(90deg, rgba(47,140,255,.35), rgba(47,140,255,.12));
    border: 1px solid rgba(145,199,255,.3);
}

.workflow-number {
    font-size: 0.78rem;
    font-weight: 800;
    color: #8fc5ff !important;
    text-transform: uppercase;
    letter-spacing: .05em;
}

.workflow-title {
    font-size: 1.02rem;
    font-weight: 750;
    margin-top: 0.1rem;
}

.workflow-copy {
    font-size: 0.84rem;
    color: #c9ddf6 !important;
    line-height: 1.35;
}

.sidebar-support {
    border: 1px solid rgba(145,199,255,.3);
    background: rgba(27,105,201,.24);
    border-radius: 14px;
    padding: 1rem;
    line-height: 1.45;
    font-size: .92rem;
    color: #eaf4ff !important;
}

/* ---------- Hero ---------- */
.hero {
    position: relative;
    overflow: hidden;
    padding: 0.45rem 0 1.15rem;
}

.hero-title {
    font-size: clamp(2.15rem, 3.6vw, 3.2rem);
    line-height: 1.04;
    font-weight: 850;
    letter-spacing: -0.045em;
    color: var(--navy) !important;
    margin: 0;
}

.hero-sub {
    font-size: 1.14rem;
    line-height: 1.5;
    color: #536a86 !important;
    margin-top: 0.55rem;
    max-width: 820px;
}

.invoice-icons {
    font-size: 2.1rem;
    letter-spacing: .3rem;
    margin-top: .5rem;
}

/* ---------- Cards ---------- */
.section-card {
    background: rgba(255,255,255,.96);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.35rem;
    box-shadow: 0 8px 28px rgba(18, 56, 99, .07);
    margin: 1rem 0;
}

.section-title {
    color: var(--navy) !important;
    font-size: 1.45rem;
    font-weight: 800;
    margin-bottom: .2rem;
}

.section-copy {
    color: var(--muted) !important;
    font-size: .98rem;
}

.step-card {
    min-height: 108px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: #fbfdff;
    padding: 1rem;
}

.step-num {
    color: var(--blue);
    font-size: .8rem;
    font-weight: 850;
    text-transform: uppercase;
    letter-spacing: .06em;
}

.step-title {
    color: var(--navy) !important;
    font-size: 1.02rem;
    font-weight: 800;
    margin: .25rem 0;
}

.step-copy {
    color: var(--muted) !important;
    font-size: .88rem;
    line-height: 1.35;
}

/* ---------- Streamlit controls ---------- */
[data-testid="stFileUploader"] {
    background: var(--blue-soft);
    border: 2px dashed #8dbbfa;
    border-radius: 16px;
    padding: .35rem;
}

[data-testid="stFileUploaderDropzone"] {
    background: rgba(255,255,255,.55) !important;
    border-radius: 13px !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] * {
    color: var(--navy) !important;
    font-size: 1rem !important;
}

.stButton > button,
.stDownloadButton > button {
    border-radius: 10px !important;
    min-height: 2.9rem !important;
    font-size: 1rem !important;
    font-weight: 800 !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #1677e8, #1769d2) !important;
    border: 0 !important;
    color: white !important;
    box-shadow: 0 6px 18px rgba(22,119,232,.22);
}

.stDownloadButton > button {
    background: linear-gradient(90deg, #168447, #20a05a) !important;
    border: 0 !important;
    color: white !important;
    box-shadow: 0 6px 18px rgba(22,132,71,.18);
}

/* ---------- Uploaded files ---------- */
.file-card {
    background: #f2fbf6;
    border: 1px solid #ccebd8;
    border-radius: 11px;
    padding: .72rem .9rem;
    margin-bottom: .5rem;
    color: #145b35 !important;
    font-size: .92rem;
}

/* ---------- Metrics ---------- */
.metric-card {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem;
    min-height: 108px;
}

.metric-label {
    color: var(--muted) !important;
    font-size: .84rem;
    font-weight: 700;
}

.metric-value {
    color: var(--navy) !important;
    font-size: 1.8rem;
    line-height: 1.15;
    font-weight: 850;
    margin-top: .2rem;
}

.metric-note {
    color: var(--muted) !important;
    font-size: .76rem;
}

/* ---------- Review ---------- */
.review-card {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    min-height: 135px;
    box-shadow: 0 4px 16px rgba(18,56,99,.05);
    margin-bottom: .8rem;
}

.review-file {
    color: var(--navy) !important;
    font-size: 1rem;
    font-weight: 800;
    overflow-wrap: anywhere;
}

.review-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    margin-top: .7rem;
}

.review-label {
    color: var(--muted) !important;
    font-size: .8rem;
    font-weight: 700;
}

.review-value {
    color: var(--navy) !important;
    font-size: 1.05rem;
    font-weight: 800;
}

.status-valid {
    display: inline-block;
    background: var(--green-soft);
    color: var(--green) !important;
    border: 1px solid #bfe5ce;
    border-radius: 999px;
    padding: .28rem .65rem;
    font-size: .8rem;
    font-weight: 800;
}

.status-warning {
    display: inline-block;
    background: var(--amber-soft);
    color: var(--amber) !important;
    border: 1px solid #f0d49b;
    border-radius: 999px;
    padding: .28rem .65rem;
    font-size: .8rem;
    font-weight: 800;
}

.warning-card {
    background: var(--amber-soft);
    border: 1px solid #f0d49b;
    border-radius: 10px;
    padding: .7rem .85rem;
    margin-top: .65rem;
    color: #7a4b00 !important;
    font-size: .86rem;
}

/* ---------- Dataframe ---------- */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}

/* Make standard text larger / darker */
p, li, label, [data-testid="stCaptionContainer"],
[data-testid="stMarkdownContainer"] {
    color: #334967;
}

/* Hide default Streamlit decoration */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------- Sidebar: navigation-free workflow ----------
with st.sidebar:
    st.markdown('<div class="sidebar-brand">⚡ Pulsora</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Utility Invoice Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-line"></div>', unsafe_allow_html=True)

    steps = [
        ("01", "Upload", "Add one or more utility invoice files."),
        ("02", "AI Extraction", "Identify and structure key invoice fields."),
        ("03", "Review", "Validate extracted data and confidence."),
        ("04", "Export", "Download the consolidated CSV."),
    ]
    for number, title, copy in steps:
        active = title == "Upload"
        cls = "workflow-item active" if active else "workflow-item"
        st.markdown(
            f'''
            <div class="{cls}">
                <div class="workflow-number">{number}</div>
                <div class="workflow-title">{title}</div>
                <div class="workflow-copy">{copy}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sidebar-line"></div>', unsafe_allow_html=True)
    st.markdown(
        '''
        <div class="sidebar-support">
            ⚡ &nbsp; 🔥 &nbsp; 💧<br><br>
            Supports <b>electricity, gas and water</b> invoices across different layouts and languages, including PDF and image files.
        </div>
        ''',
        unsafe_allow_html=True,
    )

# ---------- Hero ----------
st.markdown(
    '''
    <div class="hero">
        <div class="hero-title">Utility Invoice Intelligence</div>
        <div class="hero-sub">Upload utility invoices (PDF, JPG, JPEG or PNG) and extract key details into a clean CSV with AI.</div>
        <div class="invoice-icons">⚡ &nbsp; 🔥 &nbsp; 💧</div>
    </div>
    ''',
    unsafe_allow_html=True,
)

# ---------- Three-step overview ----------
c1, c2, c3 = st.columns(3)
for col, num, title, copy in [
    (c1, "01", "Upload Invoice Files", "Add one or more utility invoices."),
    (c2, "02", "AI Extraction", "Identify and structure key invoice fields."),
    (c3, "03", "Review & Download", "Review results and export the consolidated CSV."),
]:
    with col:
        st.markdown(
            f'''
            <div class="step-card">
                <div class="step-num">{num}</div>
                <div class="step-title">{title}</div>
                <div class="step-copy">{copy}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

# ---------- Upload ----------
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Upload Invoice Files</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-copy">Drag & drop one or more invoice files here. PDF, JPG, JPEG and PNG supported • electricity, gas and water • multilingual invoices supported.</div>',
    unsafe_allow_html=True,
)

uploaded = st.file_uploader(
    "Select invoice files",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="Select one or more utility invoice files (PDF, JPG, JPEG or PNG).",
    label_visibility="collapsed",
)
st.markdown('</div>', unsafe_allow_html=True)

if not uploaded:
    st.markdown(
        '''
        <div class="section-card">
            <div class="section-title">Ready to process</div>
            <div class="section-copy">Upload one or more utility invoices to begin extraction.</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    st.stop()

# ---------- Uploaded files ----------
st.markdown('<div class="section-title">Uploaded Invoices</div>', unsafe_allow_html=True)
st.markdown('<div class="section-copy">Review the files selected for this extraction run.</div>', unsafe_allow_html=True)

file_cols = st.columns(2)
for idx, f in enumerate(uploaded):
    with file_cols[idx % 2]:
        st.markdown(
            f'<div class="file-card">📄 &nbsp; <b>{f.name}</b> &nbsp; • &nbsp; {f.size / 1024:.0f} KB</div>',
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
process = st.button("⚡ Process Invoices", type="primary", use_container_width=True)

# ---------- Processing: ORIGINAL EXTRACTION LOGIC PRESERVED ----------
if process:
    results = []
    errors = []

    for f in uploaded:
        with st.status(f"Processing {f.name}...", expanded=True) as status:
            try:
                raw = f.read()
                file_type = f.type or Path(f.name).suffix.lower()
                st.write("Extracting invoice content...")
                extracted = extract_text_and_pages(raw, file_type=file_type)

                if extracted.text.strip():
                    st.write("Selectable text detected — using text extraction.")
                else:
                    st.write("Scanned/image-only invoice detected — using visual AI extraction.")

                st.write("Sending structured extraction request to the LLM...")
                data = parse_invoice(extracted.text, extracted.page_images)

                st.write("Validating extracted fields...")
                validated, warnings = validate_invoice(data)

                result = validated.model_dump()
                result["_filename"] = f.name
                result["_warnings"] = warnings
                results.append(result)

                status.update(label=f"{f.name} processed", state="complete")
            except Exception as exc:
                errors.append((f.name, str(exc)))
                status.update(label=f"{f.name} failed", state="error")

    if results:
        st.session_state["invoice_results"] = results
        st.session_state["last_files"] = {f.name: f.getvalue() for f in uploaded}

    if errors:
        st.error("Some invoices could not be processed.")
        for name, err in errors:
            st.write(f"**{name}:** {err}")

# ---------- Results ----------
results = st.session_state.get("invoice_results", [])
if results:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-card">', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Extraction Results</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-copy">{len(results)} invoice{"s" if len(results) != 1 else ""} processed and validated. Review the extracted data below.</div>',
        unsafe_allow_html=True,
    )

    df = pd.DataFrame(results)

    # Summary metrics
    confidence_values = [r.get("confidence") for r in results if r.get("confidence") is not None]
    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else None
    warning_count = sum(1 for r in results if r.get("_warnings"))
    valid_count = len(results) - warning_count

    m1, m2, m3, m4 = st.columns(4)
    metric_data = [
        (m1, "Invoices Processed", str(len(results)), "Records extracted"),
        (m2, "Validated Records", str(valid_count), "No validation warnings" if warning_count == 0 else f"{warning_count} need review"),
        (m3, "Average Confidence", f"{avg_confidence:.0%}" if avg_confidence is not None else "N/A", "Across processed invoices"),
        (m4, "Warnings", str(warning_count), "Validation warnings"),
    ]
    for col, label, value, note in metric_data:
        with col:
            st.markdown(
                f'''
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-note">{note}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

    display_cols = [
        "_filename", "vendor_name", "invoice_date", "service_address", "utility_type",
        "usage_amount", "usage_unit", "billing_period_start",
        "billing_period_end", "confidence"
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    shown = df[display_cols].copy()
    rename_map = {
        "_filename": "File Name",
        "vendor_name": "Vendor Name",
        "invoice_date": "Invoice Date",
        "service_address": "Service Address",
        "utility_type": "Utility Type",
        "usage_amount": "Usage Amount",
        "usage_unit": "Unit",
        "billing_period_start": "Billing Period Start",
        "billing_period_end": "Billing Period End",
        "confidence": "Confidence",
    }
    shown = shown.rename(columns=rename_map)

    if "Confidence" in shown.columns:
        shown["Confidence"] = shown["Confidence"].apply(
            lambda x: f"{x:.0%}" if isinstance(x, (float, int)) else x
        )

    st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)
    st.dataframe(
        shown,
        use_container_width=True,
        hide_index=True,
        height=min(600, max(220, 64 + (len(shown) * 58))),
    )

    # ---------- Review: all invoices shown, no selected invoice ----------
    st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Review</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Confidence and validation status for every processed invoice. All invoices are shown together.</div>',
        unsafe_allow_html=True,
    )

    review_cols = st.columns(2)
    for idx, result in enumerate(results):
        with review_cols[idx % 2]:
            filename = result.get("_filename", "Invoice")
            confidence = result.get("confidence")
            warnings = result.get("_warnings", []) or []
            confidence_text = f"{confidence:.0%}" if confidence is not None else "N/A"

            if warnings:
                status_html = '<span class="status-warning">⚠ Review required</span>'
            else:
                status_html = '<span class="status-valid">✓ Validation passed</span>'

            warning_html = ""
            if warnings:
                warning_items = "".join(f"<li>{w}</li>" for w in warnings)
                warning_html = f'<div class="warning-card"><b>Validation details</b><ul style="margin:.35rem 0 0 1.1rem; padding:0;">{warning_items}</ul></div>'

            st.markdown(
                f'''
                <div class="review-card">
                    <div class="review-file">📄 {filename}</div>
                    <div class="review-row">
                        <div>
                            <div class="review-label">Confidence</div>
                            <div class="review-value">{confidence_text}</div>
                        </div>
                        <div style="text-align:right">
                            <div class="review-label">Status</div>
                            <div style="margin-top:.18rem">{status_html}</div>
                        </div>
                    </div>
                    {warning_html}
                </div>
                ''',
                unsafe_allow_html=True,
            )

    # ---------- Export ----------
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Export</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-copy">Download the consolidated extraction as CSV.</div>', unsafe_allow_html=True)

    csv_df = df.drop(columns=["_warnings"], errors="ignore")
    csv_bytes = csv_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇ Download CSV",
        data=csv_bytes,
        file_name="pulsora_invoice_extraction.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)
