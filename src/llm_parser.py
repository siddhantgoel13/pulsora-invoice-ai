import base64
import json
from typing import Any

from openai import OpenAI

from .models import InvoiceData


def _image_to_data_url(image: bytes | str) -> str:
    """Convert rendered PDF page bytes into an OpenAI-compatible image URL."""
    if isinstance(image, str):
        # Already a URL/data URL; leave it unchanged.
        return image

    if not isinstance(image, (bytes, bytearray)):
        raise TypeError(f"Unsupported page image type: {type(image).__name__}")

    encoded = base64.b64encode(bytes(image)).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _build_prompt(text: str) -> str:
    return f"""
You are extracting structured data from a utility invoice.

Use the invoice text below as supporting evidence. The application also provides
the rendered invoice page images to the model, so use the visual layout and
labels on the invoice as the primary source when text order is ambiguous.

Return ONLY valid JSON matching this schema:

{{
  "vendor_name": string | null,
  "invoice_date": "YYYY-MM-DD" | null,
  "service_address": string | null,
  "utility_type": "electricity" | "gas" | "water" | null,
  "usage_amount": number | null,
  "usage_unit": string | null,
  "billing_period_start": "YYYY-MM-DD" | null,
  "billing_period_end": "YYYY-MM-DD" | null,
  "confidence": number,
  "evidence": {{
      "invoice_date": string | null,
      "usage": string | null,
      "billing_period": string | null
  }}
}}

IMPORTANT FIELD RULES

1. INVOICE DATE
- Use a date explicitly labelled Invoice Date, Bill Date, Billing Date,
  Issue Date, Statement Date, or an equivalent label.
- NEVER use Due Date, Payment Due Date, Disconnect Date, or a payment deadline
  as invoice_date.
- If there is no explicit invoice/bill/issue date, return null.
- Do not infer invoice_date from the billing period.

2. USAGE
- Extract actual utility consumption/usage.
- Valid labels include Consumption, Usage, Amount Used, Units Consumed,
  Energy Used, Gas Used, Water Used, or equivalent.
- NEVER use No. of Days / Bill Days as usage.
- NEVER use meter readings as usage.
- NEVER use a rate, charge, amount due, tax, account number, or invoice number.
- Usage must be a physical quantity of utility consumed, paired with a physical utility unit.
- Currency is NEVER a valid usage unit. Reject €, $, £, ₹, INR, EUR, USD, GBP, and similar currency units.
- A monetary statement such as "average daily cost" or "average daily consumption cost" is a cost, NOT utility usage.
- NEVER use monetary cost/charge values merely because the surrounding label contains
  "consumption", "consumo", "usage", or an equivalent word.
- Do not use a percentage, temperature, number of days, tariff/rate, or other non-physical
  measurement as usage.
- If the invoice contains multiple separate consumption-period rows for the
  same invoice, identify ALL of those consumption values.
- If there is an explicit total consumption value, prefer that total.
- Otherwise, if the separate rows clearly represent additive consumption
  periods for the same invoice and have the same unit, SUM THEM.
- Example: 20.316 SCM + 2.684 SCM = 23.000 SCM.
- Do NOT sum meter readings or unrelated numeric fields.
- If the only consumption-related number is monetary (for example 1.72 €), return
  usage_amount=null and usage_unit=null rather than treating the monetary value as usage.

3. BILLING PERIOD
- Extract the service/usage period explicitly labelled From/To, Billing
  Period, Service Period, Reading Period, or equivalent.
- Do not substitute invoice date or due date for billing period dates.

4. EVIDENCE
- For invoice_date, usage, and billing_period, provide a short description
  of the exact label/value relationship used.
- If usage was calculated from multiple periods, explicitly list the
  components and total in the usage evidence.

5. MISSING / AMBIGUOUS
- Prefer null over guessing.
- Do not manufacture a date or usage value.

INVOICE TEXT:
{text}
"""


def _audit_prompt(first_pass: dict[str, Any]) -> str:
    return f"""
Audit this first-pass utility invoice extraction against the invoice image.

FIRST-PASS RESULT:
{json.dumps(first_pass, ensure_ascii=False)}

Correct ONLY fields that are contradicted by the visible invoice.

Rules:
- Due Date must never become invoice_date.
- No. of Days / Bill Days must never become usage.
- Meter readings must never become usage.
- Usage must represent a physical utility quantity, not a monetary cost.
- Currency units (€, $, £, ₹, INR, EUR, USD, GBP, etc.) are never valid usage units.
- Reject statements such as "average daily cost" even when they contain the word
  consumption/consumo; they describe money, not physical usage.
- If the first pass selected a monetary value as usage, set usage_amount and usage_unit to null.
- If multiple clearly additive consumption periods exist, sum them when there
  is no explicit total. For example, 20.316 SCM + 2.684 SCM = 23.000 SCM.
- If there is an explicit total consumption, use the total instead of summing
  unrelated numbers.
- If no explicit invoice/bill/issue date exists, invoice_date must be null.
- Preserve correct fields rather than changing them unnecessarily.

Return ONLY the same JSON schema as the first pass, including evidence.
"""


def _normalise(result: dict[str, Any]) -> InvoiceData:
    fields = {
        "vendor_name": result.get("vendor_name"),
        "invoice_date": result.get("invoice_date"),
        "service_address": result.get("service_address"),
        "utility_type": result.get("utility_type"),
        "usage_amount": result.get("usage_amount"),
        "usage_unit": result.get("usage_unit"),
        "billing_period_start": result.get("billing_period_start"),
        "billing_period_end": result.get("billing_period_end"),
        "confidence": result.get("confidence"),
    }
    return InvoiceData(**fields)


def _build_multimodal_content(text: str, page_images: list[bytes | str] | None):
    content: list[dict[str, Any]] = [
        {"type": "text", "text": text}
    ]

    for image in (page_images or []):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": _image_to_data_url(image),
                "detail": "high",
            },
        })

    return content


def parse_invoice(
    text: str,
    page_images: list[bytes | str] | None = None,
    client: OpenAI | None = None,
) -> InvoiceData:
    """
    Extract invoice fields using text + rendered invoice images.

    V5.1 fixes the V5 image-input serialization error:
    PDF page images are bytes internally, but OpenAI image_url requires a
    string URL/data URL. Images are therefore base64 encoded before sending.

    It also retains the V5 consumption logic for invoices containing multiple
    additive usage periods.
    """
    if client is None:
        client = OpenAI()

    content = _build_multimodal_content(
        _build_prompt(text),
        page_images,
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a highly accurate utility-invoice extraction "
                    "engine. Never guess when the invoice is ambiguous."
                ),
            },
            {"role": "user", "content": content},
        ],
    )

    first_pass = json.loads(response.choices[0].message.content)

    # Second pass: challenge the extraction using the same invoice evidence.
    audit_content = _build_multimodal_content(
        _audit_prompt(first_pass),
        page_images,
    )

    audit_response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the final quality-control reviewer for utility "
                    "invoice extraction."
                ),
            },
            {"role": "user", "content": audit_content},
        ],
    )

    audited = json.loads(audit_response.choices[0].message.content)
    return _normalise(audited)
