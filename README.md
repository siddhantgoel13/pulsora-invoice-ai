# Pulsora — Utility Invoice Intelligence

Pulsora is an AI-powered utility invoice extraction application that converts electricity, gas, and water invoices into structured data and a consolidated CSV.

The application is designed to handle invoices with different layouts and languages, including both text-based and image/scanned documents.

## What Pulsora Does

Pulsora provides an end-to-end invoice extraction workflow:

1. Upload one or more utility invoice files.
2. Extract invoice text and/or page images.
3. Use a multimodal LLM to identify the required invoice fields.
4. Run deterministic validation and normalization.
5. Display confidence and validation status for each invoice.
6. Flag invoices that require manual review.
7. Export the consolidated results as CSV.

## Supported Documents

- PDF
- JPG
- JPEG
- PNG

The application supports utility invoices for:

- Electricity
- Gas
- Water

Multilingual invoices are supported where the relevant information can be identified from the document.

## Extracted Fields

The current extraction schema includes:

| Field | Description |
|---|---|
| Vendor Name | Utility provider / issuer |
| Invoice Date | Explicit invoice, bill, issue, or equivalent date |
| Service Address | Address associated with the service |
| Utility Type | Electricity, gas, or water |
| Usage Amount | Actual utility consumption |
| Usage Unit | Unit associated with consumption |
| Billing Period Start | Start of the service/billing period |
| Billing Period End | End of the service/billing period |
| Confidence | Overall extraction confidence |

The CSV also includes the source filename so that extracted records can be traced back to the uploaded invoice.

## Extraction Approach

Pulsora combines document processing, multimodal AI extraction, and deterministic validation.

```text
PDF / JPG / JPEG / PNG
          |
          v
Document extraction
(text + page images)
          |
          v
Multimodal LLM extraction
          |
          v
Structured JSON
          |
          v
Pydantic normalization
          |
          v
Deterministic validation
          |
          v
Confidence + review status
          |
          v
Consolidated CSV
```

### PDF handling

For PDFs, the application uses PyMuPDF to:

- Extract selectable text when available.
- Render invoice pages as images.
- Provide both textual and visual evidence to the multimodal extraction layer.

This also supports scanned/image-only PDFs because the rendered page images can be used for visual extraction.

### Image handling

JPG, JPEG, and PNG invoices are normalized to JPEG page images and passed through the same multimodal extraction workflow.

This allows the same extraction and validation pipeline to be used for both traditional PDF invoices and standalone invoice images.

## AI Extraction and Validation

The extraction prompt explicitly distinguishes important invoice fields to reduce common extraction errors.

For example:

- Invoice Date is taken from an explicitly labelled invoice/bill/issue/statement date.
- Due Date is not treated as Invoice Date.
- Bill Days / Number of Days is not treated as Usage.
- Meter readings are not treated as Usage.
- Rates, charges, taxes, account numbers, and invoice numbers are not treated as Usage.
- When an invoice contains multiple clearly additive consumption periods, the consumption values can be combined when appropriate.
- Ambiguous or unavailable values are returned as null rather than being invented.

A second AI audit pass reviews the first extraction against the invoice evidence before the result is normalized.

After the AI extraction, deterministic validation checks for issues such as:

- Missing invoice date
- Missing usage
- Missing usage unit
- Unexpected utility type
- Negative usage
- Invalid billing-period ordering
- Low or moderate confidence
- Other date consistency concerns

Invoices requiring additional attention are shown as **Review required** rather than being silently treated as error-free.

## Technology

- Python
- Streamlit
- OpenAI API
- PyMuPDF
- Pillow
- Pydantic
- Pandas

The current application uses a multimodal OpenAI model for invoice extraction and a second pass for extraction quality control.

## Project Structure

```text
Pulsora/
├── app.py
├── src/
│   ├── extractor.py
│   ├── llm_parser.py
│   ├── models.py
│   └── validator.py
├── requirements.txt
└── README.md
```

### Component responsibilities

**`app.py`**
- Streamlit UI
- File upload
- Processing workflow
- Review interface
- CSV export

**`src/extractor.py`**
- PDF text extraction
- PDF page rendering
- JPG/JPEG/PNG normalization

**`src/llm_parser.py`**
- Extraction prompt
- Multimodal LLM request
- Structured response handling
- Second-pass extraction audit

**`src/models.py`**
- Pydantic invoice data model
- Field normalization

**`src/validator.py`**
- Deterministic validation
- Review warnings
- Confidence checks

## Running Locally

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key"
```

Start the application:

```bash
streamlit run app.py
```

The application will be available at:

```text
http://localhost:8501
```

## Configuration

The application requires an OpenAI API key.

For Streamlit Cloud or another deployment platform, configure `OPENAI_API_KEY` through the platform's secret/environment-variable configuration rather than committing credentials to the repository.

## Output

The application produces a consolidated CSV containing one extracted record per successfully processed invoice.

The review interface shows:

- Source filename
- Extracted fields
- Confidence
- Validation status
- Review warnings where applicable

## Guardrails and Human Review

Pulsora is designed to avoid silently presenting uncertain extraction as fact.

The application:

- Prefers explicit invoice evidence over inference.
- Returns missing/ambiguous values as null.
- Validates extracted values after the AI response.
- Displays confidence information.
- Flags records requiring manual review.
- Keeps the original invoice filename with the extracted record.

AI extraction should therefore be treated as an assisted document-processing workflow rather than a guarantee of perfect data accuracy.

## Current Scope

The current version focuses on:

- Utility invoice extraction
- Multi-file processing
- PDF and image inputs
- Multilingual invoice layouts
- Structured field extraction
- Validation and confidence review
- CSV export

The project intentionally avoids unnecessary workflow complexity such as user accounts, databases, or enterprise document-management features.

## Demonstration

The demonstration dataset includes utility invoices representing different:

- Countries
- Languages
- Utility types
- Invoice layouts
- Document formats

This is intended to demonstrate that the extraction pipeline is not dependent on a single invoice template.

## Future Enhancements

Potential future improvements include:

- Field-level confidence scores
- Larger automated evaluation datasets with ground-truth labels
- More extensive OCR/document preprocessing
- Cost and latency monitoring
- Retry/fallback model handling
- Human-review workflows for individual fields
- Additional utility providers and invoice formats
