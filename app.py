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
    page_title="Pulsora — Invoice to CSV",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 1500px; }
    .hero-title { font-size: 2.25rem; font-weight: 800; color: #18212f; margin-bottom: .25rem; letter-spacing: -.02em; }
    .hero-sub { color: #4b5563; font-size: 1.08rem; margin-bottom: 1.35rem; }
    .step { border-radius: 10px; padding: .9rem 1rem; background: #f8fafc; border: 1px solid #dfe5ec; text-align: center; min-height: 86px; }
    .upload-box { border: 1.5px dashed #9aa7b5; border-radius: 12px; padding: 1.5rem; background: #f8fafc; }
    .small-muted { color: #5f6b78; font-size: .92rem; }
    .review-card { border: 1px solid #dfe5ec; border-radius: 12px; padding: 1rem 1.1rem; background: #ffffff; margin-bottom: .75rem; }
    .review-title { font-size: 1.05rem; font-weight: 700; color: #1f2937; margin-bottom: .35rem; }
    .review-meta { color: #4b5563; font-size: .95rem; line-height: 1.55; }
    div[data-testid="stMetric"] { border: 1px solid #dfe5ec; padding: 14px; border-radius: 10px; background: #ffffff; }
    p, li, label, .stCaption, [data-testid="stMarkdownContainer"] { color: #374151; }
    [data-testid="stDataFrame"] { border: 1px solid #dfe5ec; border-radius: 10px; }
    div.stButton > button[kind="primary"], div.stDownloadButton > button { font-weight: 700; min-height: 2.7rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## ⚡ Pulsora")
    st.caption("AI Utility Invoice Extraction")
    st.divider()

    st.markdown("### Invoice workflow")
    st.markdown(
        """
        <div class="review-meta">
        <b>1. Upload</b><br>
        Add one or more utility invoice PDFs.<br><br>
        <b>2. Extract</b><br>
        AI identifies and structures invoice fields.<br><br>
        <b>3. Review</b><br>
        Validate the extracted data and confidence.<br><br>
        <b>4. Export</b><br>
        Download the consolidated CSV.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.info(
        "Supports electricity, gas and water invoices across different layouts "
        "and languages."
    )

# ---------- Header ----------
st.markdown('<div class="hero-title">Turn Utility Invoices into Structured Data</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Upload an invoice (PDF) and extract key details into a clean CSV with AI.</div>',
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**① Upload Invoice**")
    st.caption("Select one or more PDF invoices")
with c2:
    st.markdown("**② AI Extraction**")
    st.caption("Extract and validate key fields")
with c3:
    st.markdown("**③ Review & Download**")
    st.caption("Review results and export CSV")

st.divider()

uploaded = st.file_uploader(
    "Drag & drop invoice PDFs here",
    type=["pdf"],
    accept_multiple_files=True,
    help="For the take-home demo, PDF is the supported input format.",
)

if not uploaded:
    st.markdown(
        """
        <div class="upload-box">
            <h3 style="margin:0">Upload Utility Invoices</h3>
            <p class="small-muted">PDF files • electricity, gas, water • multilingual invoices supported</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("###")
    st.write("**Demo dataset**")
    st.caption("The repository includes five real public utility documents used to test the pipeline.")
    demo_files = [p.name for p in sorted((Path(__file__).parent / "invoices").glob("*.pdf"))]
    if demo_files:
        st.dataframe(pd.DataFrame({"Sample invoice": demo_files}), use_container_width=True, hide_index=True)
    st.stop()

# ---------- Uploaded file list ----------
st.markdown("### Uploaded invoices")
for f in uploaded:
    st.success(f"{f.name}  •  {f.size / 1024:.0f} KB")

process = st.button("⚡ Process Invoices", type="primary", use_container_width=True)

if process:
    results = []
    errors = []

    for f in uploaded:
        with st.status(f"Processing {f.name}...", expanded=True) as status:
            try:
                raw = f.read()
                st.write("Extracting PDF text...")
                extracted = extract_text_and_pages(raw)

                if extracted.text.strip():
                    st.write("Selectable text detected — using text extraction.")
                else:
                    st.write("Scanned/image-only PDF detected — using visual AI extraction.")

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
    st.divider()
    st.markdown("## Extraction Results")
    st.caption(
        f"{len(results)} invoice{'s' if len(results) != 1 else ''} processed. "
        "Review the extracted values below before downloading the CSV."
    )

    df = pd.DataFrame(results)

    display_cols = [
        "vendor_name", "invoice_date", "service_address", "utility_type",
        "usage_amount", "usage_unit", "billing_period_start",
        "billing_period_end", "confidence", "_filename"
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    st.markdown("### Extracted Data")
    shown = df[display_cols].copy()
    shown.columns = [c.replace("_", " ").title() for c in shown.columns]

    st.dataframe(
        shown,
        use_container_width=True,
        hide_index=True,
        height=min(520, max(180, 58 + (len(shown) * 55))),
    )

    st.markdown("### Review")
    st.caption(
        "Confidence and validation status for every processed invoice. "
        "No invoice is selected by default."
    )

    review_cols = st.columns(min(3, max(1, len(results))))

    for idx, result in enumerate(results):
        with review_cols[idx % len(review_cols)]:
            filename = result.get("_filename", "Invoice")
            confidence = result.get("confidence")
            warnings = result.get("_warnings", [])

            confidence_text = (
                f"{confidence:.0%}" if confidence is not None else "N/A"
            )
            status_text = "⚠️ Review warnings" if warnings else "✓ Validation passed"

            review_html = f'''
            <div class="review-card">
                <div class="review-title">{filename}</div>
                <div class="review-meta">
                    <b>Confidence:</b> {confidence_text}<br>
                    <b>Status:</b> {status_text}
                </div>
            </div>
            '''

            st.markdown(review_html, unsafe_allow_html=True)

            if warnings:
                for warning in warnings:
                    st.warning(warning, icon="⚠️")
            else:
                st.success("Validation passed with no warnings.", icon="✓")

    st.markdown("### Export")
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

