import base64
import json
import os
from typing import Any

from openai import OpenAI

from .models import InvoiceData


SYSTEM_PROMPT = """
You are a high-accuracy utility-invoice extraction engine.

Your job is to extract structured data from electricity, gas, and water invoices.
You will receive BOTH:
1) selectable PDF text, when available, and
2) rendered invoice page images.

The image/layout is authoritative when text extraction loses table relationships.

Return ONLY valid JSON.

Required output:
{
  "vendor_name": string|null,
  "invoice_date": "YYYY-MM-DD"|null,
  "service_address": string|null,
  "utility_type": "electricity"|"gas"|"water"|null,
  "usage_amount": number|null,
  "usage_unit": string|null,
  "billing_period_start": "YYYY-MM-DD"|null,
  "billing_period_end": "YYYY-MM-DD"|null,
  "confidence": number,
  "evidence": {
    "invoice_date_label": string|null,
    "invoice_date_value": string|null,
    "usage_label": string|null,
    "usage_value_text": string|null,
    "billing_period_text": string|null
  }
}

CRITICAL DATE RULES:
- invoice_date means the date explicitly associated with Invoice Date, Bill Date,
  Issue Date, Statement Date, or an equivalent label.
- NEVER use Due Date, Payment Due Date, Disconnect Date, or a billing-period
  date as invoice_date.
- If there is no explicit invoice/bill/issue/statement date, return invoice_date=null.
- Do not infer an invoice date from the due date.
- Use the visual position of the label and value together. A nearby date is not
  enough if its label belongs to a different field.

CRITICAL USAGE RULES:
- usage_amount means actual utility consumption.
- NEVER use No. of Days / Bill Days as usage.
- NEVER use meter readings as usage.
- NEVER use rate, tariff, price, tax, subtotal, total amount, balance, or account
  number as usage.
- Prefer values explicitly labelled Consumption, Usage, Amount Used, Units
  Consumed, Energy Used, Gas Used, Water Used, etc.
- If consumption is split across multiple service/reading periods and the invoice
  presents separate consumption quantities that together make up the billed
  consumption, ADD those quantities.
- Example: 20.316 SCM + 2.684 SCM = 23.000 SCM.
- Do not add meter readings.
- The usage unit must come from the same consumption field/table as the selected
  usage amount whenever possible.

CRITICAL BILLING-PERIOD RULES:
- billing_period_start/end are the service/consumption period dates.
- Prefer explicit From/To, Service Period, Billing Period, or equivalent labels.
- Do not use invoice date or due date unless the document explicitly defines it
  as the service period.

GENERAL:
- Never invent information.
- If evidence is insufficient, return null.
- Preserve the invoice's original utility terminology, but normalize common
  units such as SCM, kWh, m3, gallons.
- Normalize dates to YYYY-MM-DD.
- confidence must be between 0 and 1.
- Evidence strings must be short and copied/paraphrased from the invoice, not invented.
"""


AUDIT_PROMPT = """
You are the final quality-control reviewer for a utility invoice extraction.

You receive the invoice text, invoice images, and a first-pass extraction.

Re-check the FIRST-PASS fields against the actual invoice. Correct them rather
than merely accepting them.

Pay particular attention to:
1. Invoice date versus Due Date.
2. Usage versus No. of Days.
3. Usage versus meter readings.
4. Multiple consumption rows that need to be summed.
5. Billing period versus invoice/due dates.

Hard rules:
- A value labelled "Due Date" or "Payment Due Date" can NEVER be invoice_date.
- A value labelled "No. of Days" or "Bill Days" can NEVER be usage_amount.
- Meter readings can NEVER be usage_amount.
- If multiple consumption values are clearly separate components of the billed
  consumption, sum them.
- If no explicit invoice/bill/issue/statement date exists, invoice_date=null.
- If usage cannot be established reliably, usage_amount=null.
- Do not guess.

Return the same JSON structure as the first-pass extraction.
"""


def _image_data_url(image_bytes: bytes) -> str:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def _build_visual_content(text: str, page_images: list[bytes] | None) -> list[dict[str, Any]]:
    images = (page_images or [])[:12]

    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Extract this utility invoice using BOTH the PDF text and the "
                "invoice images. Treat the visual layout and field labels as "
                "authoritative when text extraction is ambiguous.\n\n"
                "PDF TEXT:\n"
                f"{text[:120000]}"
            ),
        }
    ]

    for image in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _image_data_url(image),
                    "detail": "high",
                },
            }
        )

    return content


def _json_from_response(response) -> dict[str, Any]:
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The extraction model returned an empty response.")
    return json.loads(content)


def _normalise_first_pass(payload: dict[str, Any]) -> dict[str, Any]:
    # Keep the audit contract stable even if a model omits evidence.
    evidence = payload.get("evidence") or {}
    payload["evidence"] = {
        "invoice_date_label": evidence.get("invoice_date_label"),
        "invoice_date_value": evidence.get("invoice_date_value"),
        "usage_label": evidence.get("usage_label"),
        "usage_value_text": evidence.get("usage_value_text"),
        "billing_period_text": evidence.get("billing_period_text"),
    }
    return payload


def _hard_safety_checks(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic guardrails after the LLM passes.

    These do not try to understand every invoice. They prevent known classes of
    catastrophic field swaps such as Due Date -> invoice_date and No. of Days ->
    usage.
    """
    evidence = payload.get("evidence") or {}

    date_label = str(evidence.get("invoice_date_label") or "").lower()
    if any(term in date_label for term in (
        "due date",
        "payment due",
        "disconnect",
        "late payment",
    )):
        payload["invoice_date"] = None

    usage_label = str(evidence.get("usage_label") or "").lower()
    if any(term in usage_label for term in (
        "no. of days",
        "no of days",
        "number of days",
        "bill days",
        "billing days",
        "days",
        "meter reading",
        "previous reading",
        "present reading",
    )):
        payload["usage_amount"] = None
        payload["usage_unit"] = None

    return payload


def parse_invoice(text: str, page_images: list[bytes] | None = None) -> InvoiceData:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to Streamlit Secrets before processing invoices."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    client = OpenAI(api_key=api_key)

    # Pass 1: extract using text + visual layout for every invoice.
    first_response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_visual_content(text, page_images),
            },
        ],
    )

    first_pass = _normalise_first_pass(_json_from_response(first_response))

    # Pass 2: independent visual/text audit. This is deliberately separate
    # from the first extraction so the model is asked to challenge its own
    # candidate values instead of simply formatting them.
    audit_content = _build_visual_content(text, page_images)
    audit_content.append(
        {
            "type": "text",
            "text": (
                "\nFIRST-PASS EXTRACTION TO AUDIT:\n"
                + json.dumps(first_pass, ensure_ascii=False)
                + "\n\n"
                + AUDIT_PROMPT
            ),
        }
    )

    audit_response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": AUDIT_PROMPT,
            },
            {
                "role": "user",
                "content": audit_content,
            },
        ],
    )

    audited = _json_from_response(audit_response)
    audited = _normalise_first_pass(audited)
    audited = _hard_safety_checks(audited)

    # Pydantic performs the final schema/type/date validation.
    return InvoiceData.model_validate(audited)
