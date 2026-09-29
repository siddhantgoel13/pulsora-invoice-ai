import base64
import json
import os

from openai import OpenAI

from .models import InvoiceData


SYSTEM_PROMPT = """
You are a high-accuracy utility-invoice data extraction engine.

Your job is to extract ONLY information that is explicitly supported by the
invoice. Utility invoices contain many dates, numbers, readings, charges,
payment dates and other values that look similar. You must identify each
requested field by its LABEL and SEMANTIC CONTEXT, not by position alone.

Return ONLY valid JSON matching this schema:
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

GENERAL RULES
1. Never guess. If a field cannot be established confidently, return null.
2. Prefer an explicitly labelled value over an inferred value.
3. Read the invoice in its original language. Understand equivalent labels in
   other languages.
4. Normalize dates to YYYY-MM-DD.
5. confidence must be between 0 and 1 and should reflect the reliability of
   the extracted fields, not simply whether a value was found.

INVOICE DATE — VERY IMPORTANT
- Extract the date explicitly identified as the invoice/bill/statement date.
- Accept labels such as Invoice Date, Bill Date, Billing Date, Statement Date,
  Date of Invoice, Date Issued, Issue Date and their equivalents in other
  languages.
- DO NOT use Payment Due Date, Due Date, Pay By Date, Amount Due By date,
  disconnect date, meter-reading date, service-period dates, or other dates
  merely because they are prominent.
- If there is no explicit invoice/bill/statement/issue date, return null.
- If several candidate dates exist and the document does not make their
  meaning clear, return null rather than guessing.

BILLING PERIOD
- billing_period_start/end must describe the period for which utility
  consumption is billed.
- Look for labels such as Billing Period, Service Period, From/To,
  Consumption Period, Period From/To and equivalents.
- DO NOT use invoice date or due date as a billing-period boundary unless the
  invoice explicitly labels it that way.
- A number of billing days is NOT a date and must never be used as either
  billing_period_start or billing_period_end.

USAGE AMOUNT — VERY IMPORTANT
- usage_amount means the quantity of utility actually consumed/billed.
- Look for labels such as Usage, Consumption, Amount Used, Energy Used,
  Units Used, Volume Used, Total Consumption and equivalents.
- The number must be associated with the consumption/usage concept.
- DO NOT use:
  * number of billing/service days
  * account number
  * invoice number
  * meter number
  * previous meter reading
  * current/present meter reading
  * rate/tariff
  * unit price
  * tax
  * subtotal
  * total bill amount
  * amount due
  * payment amount
- If only meter readings are present and actual consumption is not stated or
  cannot be calculated reliably, return null.
- A value such as "28 days" is NOT usage.
- For gas, examples of consumption units include SCM, m3, therms.
- For electricity, examples include kWh.
- For water, examples include gallons, m3, KL.
- usage_unit must be the unit attached to the consumption value.

UTILITY TYPE
- Must be electricity, gas, or water when clearly established.
- Infer from the utility service/vendor only when the evidence is strong.

SERVICE ADDRESS
- Extract the customer/service location if explicitly present.
- Do not substitute the utility company's mailing address.

MULTIPLE VALUES
- When several similar values appear, select the one whose label and context
  match the requested field.
- If the visual layout is clearer than the extracted text, trust the visual
  invoice evidence.
- Never select a value solely because it is the first, largest, newest, or
  most prominent number/date.

MISSING OR AMBIGUOUS DATA
- null is preferred to an incorrect value.
- An uncertain extraction should reduce confidence.
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

    # Use BOTH extracted text and page images whenever images are available.
    # Text is useful for exact characters; the rendered page preserves the
    # visual relationship between labels and values, which is critical for
    # distinguishing invoice date/due date and usage/days/meter readings.
    images = (page_images or [])[:8]

    if images:
        user_content = [
            {
                "type": "text",
                "text": (
                    "Extract the required fields from this utility invoice.\n\n"
                    "IMPORTANT: Use the rendered invoice page(s) as the primary "
                    "source for label/value relationships. The extracted text "
                    "below is supplementary and may have lost the original "
                    "layout. When text and visual layout conflict, use the "
                    "visual invoice evidence.\n\n"
                    "Before returning each value, identify the label/context "
                    "that proves it represents the requested field. Do not "
                    "substitute a due date for an invoice date or billing days "
                    "for utility consumption. Return null when the evidence "
                    "does not establish the field.\n\n"
                    "EXTRACTED PDF TEXT:\n"
                    f"{text if text.strip() else '[No selectable text]'}"
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
    else:
        user_content = (
            "Extract the required fields from this utility invoice text. "
            "Use the field-specific rules in the system prompt. "
            "Use null when the evidence is insufficient.\n\n"
            f"{text}"
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
