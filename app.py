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
    .block-container { padding-top: 1.6rem; padding-bottom: 2rem; }
    .hero-title { font-size: 2.25rem; font-weight: 750; color: #15153a; margin-bottom: .15rem; }
    .hero-sub { color: #5d6280; font-size: 1.05rem; margin-bottom: 1.2rem; }
    .step {
        border-radius: 12px; padding: .8rem 1rem; background: #f7f7ff;
        border: 1px solid #e7e7fb; text-align: center;
    }
    .upload-box {
        border: 1.5px dashed #8d7cff; border-radius: 14px; padding: 1.4rem;
        background: #fcfbff;
    }
    .small-muted { color: #747991; font-size: .88rem; }
    div[data-testid="stMetric"] { border: 1px solid #ececf5; padding: 12px; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## ⚡ Pulsora")
    st.caption("AI Utility Invoice Extraction")
    st.divider()
    st.radio(
        "Navigation",
        ["Invoice to CSV", "History", "Sample Invoices", "Settings"],
        index=0,
        label_visibility="collapsed",
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

    df = pd.DataFrame(results)
    display_cols = [
        "vendor_name", "invoice_date", "service_address", "utility_type",
        "usage_amount", "usage_unit", "billing_period_start",
        "billing_period_end", "confidence", "_filename"
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    left, right = st.columns([1.45, 1])
    with left:
        st.markdown("### Extracted Data")
        shown = df[display_cols].copy()
        shown.columns = [c.replace("_", " ").title() for c in shown.columns]
        st.dataframe(shown, use_container_width=True, hide_index=True)

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

    with right:
        st.markdown("### Review")
        selected = st.selectbox(
            "Invoice",
            [r["_filename"] for r in results],
            label_visibility="collapsed",
        )
        selected_result = next(r for r in results if r["_filename"] == selected)

        confidence = selected_result.get("confidence")
        if confidence is not None:
            st.metric("Extraction confidence", f"{confidence:.0%}")

        warnings = selected_result.get("_warnings", [])
        if warnings:
            st.warning("Validation warnings")
            for w in warnings:
                st.write(f"• {w}")
        else:
            st.success("Validation passed with no warnings.")

        st.markdown("#### Field details")
        for key, value in selected_result.items():
            if key.startswith("_") or key == "confidence":
                continue
            st.write(f"**{key.replace('_', ' ').title()}**")
            st.caption(str(value) if value is not None else "Not available")

        # Preview the uploaded PDF when available
        file_map = st.session_state.get("last_files", {})
        if selected in file_map:
            from src.extractor import render_first_page
            try:
                img = render_first_page(file_map[selected])
                st.markdown("#### Invoice Preview")
                st.image(img, use_container_width=True)
            except Exception:
                pass
