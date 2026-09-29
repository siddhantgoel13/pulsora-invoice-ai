# Pulsora — Utility Invoice AI

A focused take-home implementation for extracting structured utility-invoice data with an LLM and exporting the results to CSV.

## What it does

1. Upload one or more utility-invoice PDFs.
2. Extract selectable PDF text with PyMuPDF; if the PDF is scanned/image-only, render the pages for visual AI extraction.
3. Send either the text or invoice page images to a vision-capable LLM for structured extraction.
4. Validate and normalize the returned fields with Pydantic.
5. Review the results in a Streamlit web UI.
6. Download a consolidated CSV.

## Required fields

- Vendor name
- Invoice date
- Service address
- Utility type
- Usage amount
- Usage unit
- Billing period start
- Billing period end

The implementation also records an overall extraction confidence value and validation warnings.

## Architecture

PDF → PyMuPDF → text extraction OR visual fallback → LLM structured JSON → Pydantic validation → DataFrame → CSV

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your API key to `.env`, then:

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Tests

```bash
pytest -q
```

## Notes / tradeoffs

- A visual AI fallback is included for scanned/image-only invoices, avoiding a dependency on a system OCR binary.
- The first implementation uses direct PDF text extraction rather than an agent framework.
- The LLM is constrained to a small JSON schema and deterministic validation is applied afterward.
- Missing values are represented as null rather than inferred.
- Low-confidence results are flagged for manual review.
- The repository includes five public utility documents used for demonstration/testing.

## Future improvements

- OCR fallback for scanned PDFs
- Field-level confidence instead of only overall confidence
- Retry/fallback model handling
- Structured observability and cost/latency metrics
- Human-review workflow for low-confidence fields
- Larger evaluation dataset with expected ground truth
