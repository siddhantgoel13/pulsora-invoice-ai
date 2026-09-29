# Pulsora --- Utility Invoice Intelligence

Pulsora is an AI-powered utility invoice extraction application that
converts electricity, gas, and water invoices into structured data and a
consolidated CSV.

The application is designed to work across different invoice layouts and
languages and supports both text-based documents and image/scanned
invoices.

## What Pulsora Does

Pulsora provides an end-to-end invoice extraction workflow:

1.  Upload one or more utility invoice files.
2.  Extract document text and/or page images.
3.  Use a multimodal LLM to identify the required invoice fields.
4.  Normalize the response into a structured schema.
5.  Run deterministic validation and consistency checks.
6.  Display confidence and validation status for each invoice.
7.  Flag records that require manual review.
8.  Export the consolidated results as CSV.

## Supported Documents

Pulsora accepts:

-   PDF
-   JPG
-   JPEG
-   PNG

Supported utility categories:

-   Electricity
-   Gas
-   Water

Multilingual invoices are supported when the relevant information can be
identified from the document.

## Extracted Fields

  -----------------------------------------------------------------------
  Field                               Description
  ----------------------------------- -----------------------------------
  Vendor Name                         Utility provider / issuer

  Invoice Date                        Explicit invoice, bill, issue, or
                                      equivalent invoice date

  Service Address                     Address associated with the service

  Utility Type                        Electricity, gas, or water

  Usage Amount                        Actual utility consumption

  Usage Unit                          Unit associated with consumption

  Billing Period Start                Start of the service/billing period

  Billing Period End                  End of the service/billing period

  Confidence                          Overall extraction confidence

  Source Filename                     Original uploaded filename for
                                      traceability
  -----------------------------------------------------------------------

## Extraction Approach

Pulsora combines document processing, multimodal AI extraction,
structured normalization, and deterministic validation.

``` text
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
Structured response
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

-   Extract selectable text when available.
-   Render invoice pages as images.
-   Provide textual and visual evidence to the multimodal extraction
    layer.

This also allows scanned or image-only PDFs to be processed through
their rendered page images.

### Image handling

JPG, JPEG, and PNG invoices are normalized and passed through the same
multimodal extraction workflow.

This keeps standalone images and PDFs within the same extraction and
validation pipeline.

## AI Extraction and Validation

The extraction instructions explicitly distinguish commonly confused
invoice fields.

Examples include:

-   **Invoice Date** is taken from an explicitly labelled
    invoice/bill/issue/statement date.
-   **Due Date** is not treated as Invoice Date.
-   **Bill Days / Number of Days** is not treated as Usage.
-   **Meter readings** are not treated as Usage.
-   **Rates, charges, taxes, account numbers, and invoice numbers** are
    not treated as Usage.
-   When an invoice contains multiple clearly additive consumption
    periods, consumption can be combined when appropriate.
-   Ambiguous or unavailable values are returned as `null` rather than
    invented.

The extraction workflow also includes an AI review/audit pass before
normalization.

After AI extraction, deterministic validation checks for issues such as:

-   Missing invoice date
-   Missing usage
-   Missing usage unit
-   Unexpected utility type
-   Negative usage
-   Invalid billing-period ordering
-   Low or moderate confidence
-   Other date consistency concerns

Invoices requiring additional attention are displayed as **Review
required** instead of being silently treated as error-free.

## Guardrails and Human Review

Pulsora is designed as an assisted document-processing workflow rather
than an autonomous source of truth.

The application:

-   Prefers explicit invoice evidence over unsupported inference.
-   Returns missing or ambiguous values as `null`.
-   Validates extracted values after the AI response.
-   Displays confidence information.
-   Flags records requiring manual review.
-   Preserves the original invoice filename for traceability.
-   Avoids treating common non-usage values such as billing days, meter
    readings, rates, or charges as consumption.

This provides a clear feedback mechanism when extraction evidence is
insufficient or inconsistent.

## Technology

-   Python
-   Streamlit
-   OpenAI API
-   PyMuPDF
-   Pillow
-   Pydantic
-   Pandas

The application uses a multimodal OpenAI model for invoice extraction
and an additional AI review pass for extraction quality control.

## Project Structure

``` text
pulsora-invoice-ai/
├── .devcontainer/
├── invoices/
│   └── Final validation invoices
├── output/
│   └── Final consolidated CSV output
├── src/
│   ├── extractor.py
│   ├── llm_parser.py
│   ├── models.py
│   └── validator.py
├── tests/
│   └── test_validation.py
├── app.py
├── requirements.txt
└── README.md
```

### Component Responsibilities

**`app.py`** - Streamlit application and UI - File upload - Multi-file
processing workflow - Review interface - CSV export

**`src/extractor.py`** - PDF text extraction - PDF page rendering -
JPG/JPEG/PNG normalization

**`src/llm_parser.py`** - Extraction instructions - Multimodal LLM
request - Structured response handling - AI extraction review/audit

**`src/models.py`** - Pydantic invoice data model - Field normalization

**`src/validator.py`** - Deterministic validation - Review warnings -
Confidence and consistency checks

## Running Locally

Create a virtual environment:

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Configure the OpenAI API key as an environment variable:

``` bash
export OPENAI_API_KEY="your-api-key"
```

Start the application:

``` bash
streamlit run app.py
```

The application will be available at:

``` text
http://localhost:8501
```

## Configuration

The application requires an OpenAI API key.

For Streamlit Cloud or another deployment platform, configure
`OPENAI_API_KEY` through the platform's secret/environment-variable
configuration.

**Do not commit API keys or other secrets to the repository.**

## Output

The application produces a consolidated CSV containing one extracted
record per successfully processed invoice.

The review interface provides:

-   Source filename
-   Extracted fields
-   Confidence
-   Validation status
-   Review warnings where applicable

The final repository also includes the validation dataset and its
corresponding consolidated CSV output under `invoices/` and `output/`.

## Final Validation Dataset

The repository contains the final validation inputs used for the
submitted application, covering multiple:

-   Utility types
-   Countries
-   Languages
-   Invoice layouts
-   Document formats

The dataset includes both PDF and image-based invoice input to
demonstrate the application's document-format handling.

The corresponding consolidated CSV is included in `output/` as the
reference extraction result from the final validation run.

## Testing

The `tests/` directory contains the project's automated test coverage
for the extraction/validation components.

The final validation dataset in `invoices/` is also used as an
end-to-end smoke test for the deployed application.

## Testing Approach

Pulsora was validated using a combination of automated unit tests, manual field-level comparison against real invoices, and end-to-end smoke testing of the deployed Streamlit application.

### 1. Extraction Accuracy Validation

The final validation dataset contains utility invoices covering different providers, utility types, countries, languages, layouts, and document formats.

For the final validation run, extracted values were compared against the source invoices, with particular attention to:

- Vendor / utility provider
- Invoice date
- Service address
- Utility type
- Usage amount
- Usage unit
- Billing period start and end
- Confidence and validation status

Special attention was given to common invoice-extraction failure modes, including:

- Invoice date vs. due date
- Billing-period days vs. actual consumption
- Meter readings vs. consumption
- Monetary charges/rates vs. physical usage
- Different date formats
- Different decimal/number formats
- Missing or ambiguous fields
- Different utility units
- Multilingual labels and layouts

Where the invoice did not provide sufficient evidence for a field, the application is designed to return `null` and/or flag the record for review rather than inventing a value.

### 2. Test Cases and Edge Cases

The validation process included:

- Electricity invoices
- Gas invoices
- Water invoices
- PDF documents
- JPG/image documents
- English, French, and Spanish invoice content
- Different invoice layouts
- Different date and number formats
- Missing usage units
- Invalid billing-period ordering
- Low-confidence extraction
- Utility-type aliases
- Multiple invoices processed in a single run

A Spanish electricity invoice was also used as an edge case for distinguishing a monetary consumption-cost statement from actual physical utility consumption.

### 3. Automated Tests

The repository contains `tests/test_validation.py` with five focused validation tests covering:

1. Utility-type alias normalization (`Electric` → `electricity`)
2. Valid billing-period handling
3. Invalid billing-period detection
4. Low-confidence extraction warnings
5. Missing usage-unit warnings

The tests focus on deterministic validation and normalization behavior rather than making live LLM/API calls, which keeps them repeatable and avoids depending on external services.

### 4. End-to-End Testing

The final invoice dataset was processed through the deployed application to verify the complete workflow:

1. Upload invoice files
2. Process invoices
3. Extract structured fields
4. Run validation
5. Display confidence and review status
6. Review multiple invoice results
7. Generate and download the consolidated CSV
8. Compare the final output with the source invoices

### 5. Future Testing Improvements

With additional development time, testing could be expanded with:

- A larger labelled "golden" invoice dataset
- Automated field-level accuracy metrics
- Regression tests against every previously validated invoice
- Automated tests for multilingual extraction
- More image-quality and scanned-document cases
- OCR-specific testing for low-quality documents
- Automated UI/end-to-end browser tests
- Performance testing for larger invoice batches
- Additional utility-unit and provider-specific test cases

## Current Scope

The submitted version focuses on:

-   Utility invoice extraction
-   Multi-file processing
-   PDF and image inputs
-   Multilingual invoice layouts
-   Structured field extraction
-   Deterministic validation
-   Confidence and review status
-   CSV export
-   Human-review guardrails

The project intentionally does not introduce unnecessary enterprise
workflow features such as user accounts, databases, or
document-management systems.

## Limitations

AI-based document extraction can be affected by:

-   Poor image quality
-   Missing or unreadable invoice information
-   Highly unusual document layouts
-   Ambiguous labels or values
-   Complex tables or charts

For these cases, the application surfaces validation warnings and review
status rather than assuming that an uncertain value is correct.

## Demonstration

The final validation dataset is intended to demonstrate that the
pipeline is not dependent on a single invoice template. It includes
different utility categories, languages, layouts, and document formats.
