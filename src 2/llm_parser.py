import base64
import json
import os

from openai import OpenAI

from .models import InvoiceData


SYSTEM_PROMPT = """
You are an expert utility-bill document extraction system.

Extract ONLY the fields in the JSON schema below. Use BOTH:
1) the invoice page image(s), which are the primary source for layout and label/value relationships, and
2) the extracted PDF text, which is supporting evidence.

Return ONLY valid JSON:
{
  "vendor_name": string|null,
  "invoice_date": "YYYY-MM-DD"|null,
  "service_address": string|null,
  "utility_type": "electricity"|"gas"|"water"|null,
  "usage_amount": number|null,
  "usage_unit": string|null,
  "billing_period_start": "YYYY-MM-DD"|null,
  "billing_period_end": "YYYY-MM-DD"|null,
  "confidence": number
}

CRITICAL DATE RULES
- "invoice_date" means the date the bill/invoice was issued, printed, generated, or explicitly labelled Bill Date / Invoice Date / Issue Date.
- NEVER use Due Date, Payment Due Date, Pay By Date, Disconnect Date, Mailing Date, Meter Reading Date, or a billing-period date as invoice_date.
- If a document has only a Due Date and no invoice/bill/issue date, return invoice_date=null.
- Read the label immediately associated with the date before selecting it.
- When text extraction and the image disagree, prefer the value visibly associated with the correct label in the image.
- Do not infer an invoice date from a due date by subtracting a typical number of days.
- Normalize dates to YYYY-MM-DD.

CRITICAL USAGE RULES
- usage_amount means actual utility consumption/amount used during the billing period.
- It is NOT the number of billing days.
- It is NOT a meter reading.
- It is NOT a rate, price, charge, tax, balance, account number, or invoice number.
- Look for labels such as Usage, Amount Used, Consumption, Energy Used, Units Used, Usage History, kWh Used, Therms Used, SCM Used, gallons used, etc.
- For a table, keep the number in the same row/column as the utility service and the usage/consumption label.
- If a bill shows previous and present meter readings, do not use either reading as usage unless the invoice explicitly labels a calculated value as usage/consumption.
- If the only visible number is billing days, return usage_amount=null rather than treating days as usage.
- Keep the actual consumption unit, e.g. kWh, SCM, m3, therms, gallons.

BILLING PERIOD
- billing_period_start/end are the dates for which the consumption is billed.
- Do not use due date as either billing-period date.
- For a "From ... To ..." service period, use those dates.
- If the bill clearly gives a consumption/billing period elsewhere, use that period.

GENERAL RULES
- Never invent information.
- Use null when a field cannot be established confidently.
- Read invoices in their original language; understand equivalent labels in other languages.
- service_address should be the customer/service location, not the utility company's mailing address.
- utility_type must be electricity, gas, or water when it can be established.
- confidence must be between 0 and 1.
- Give lower confidence when a required field is ambiguous.
- Before producing JSON, internally cross-check every date and usage value against its visible label.
"""

def _image_data_url(image_bytes: bytes) -> str:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def parse_invoice(text: str, page_images: list[bytes] | None = None) -> InvoiceData:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to Streamlit Secrets before processing invoices."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    client = OpenAI(api_key=api_key)

    # Always use the invoice image when available. Text extraction alone can
    # lose the visual relationship between a label and its value (especially
    # for dates, usage, meter readings and billing days).
    images = (page_images or [])[:12]

    text_section = text.strip() if text.strip() else "(No selectable PDF text was available.)"

    user_content = [
        {
            "type": "text",
            "text": (
                "Extract the required fields from this utility invoice. "
                "The page image is the primary source; extracted text is supporting evidence. "
                "Do not guess. In particular, distinguish invoice/bill date from due date, "
                "and actual utility consumption from billing days and meter readings.\n\n"
                "EXTRACTED PDF TEXT:\n"
                f"{text_section}"
            ),
        }
    ]

    for image in images:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _image_data_url(image),
                    "detail": "high",
                },
            }
        )

    # If page images are unexpectedly unavailable, retain a text-only fallback.
    if not images:
        user_content = (
            "Extract the required fields from this utility invoice text. "
            "Use the date/usage rules in the system prompt and return null when "
            "the evidence is insufficient.\n\n"
            f"{text_section}"
        )

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    payload = json.loads(response.choices[0].message.content)
    return InvoiceData.model_validate(payload)
