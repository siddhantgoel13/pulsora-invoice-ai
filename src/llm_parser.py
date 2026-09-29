import base64
import json
import os

from openai import OpenAI

from .models import InvoiceData


SYSTEM_PROMPT = """
You extract structured data from utility invoices.

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

GENERAL RULES:
- Never invent information. Use null when a field cannot be established.
- Use BOTH the invoice image/layout and extracted PDF text as evidence when both are provided.
- Normalize dates to YYYY-MM-DD.
- utility_type must be electricity, gas, or water when it can be established.
- usage_amount must represent ACTUAL UTILITY CONSUMPTION, not money, a meter reading,
  a rate, tax, account number, invoice number, or number of billing days.
- Keep the actual consumption unit, e.g. kWh, SCM, m3, gallons.
- billing_period_start/end refer to the period for which the consumption is billed.
- confidence must be between 0 and 1.
- If a value is unreadable or absent, return null rather than guessing.

INVOICE DATE RULES:
- invoice_date must come from a field explicitly labelled Invoice Date, Bill Date,
  Issue Date, Statement Date, or an equivalent label.
- NEVER use Due Date, Payment Due Date, Amount Due Date, Disconnect Date,
  meter-reading date, or billing-period dates as invoice_date.
- If there are several dates, use the date attached to the invoice/bill/issue label,
  using the visual position on the page to determine the label-value relationship.

USAGE RULES — IMPORTANT:
- Identify the number that represents actual consumption/usage.
- NEVER interpret "No. of days", "Days", "Billing days", or similar as usage.
- NEVER use opening/previous/closing/current meter readings as usage.
- NEVER use a monetary charge or rate as usage.
- Look specifically for labels such as Consumption, Cons., Usage, Energy Used,
  Amount Used, Units Used, Quantity Consumed, or equivalent local-language labels.
- If the invoice contains MULTIPLE CONSUMPTION PERIODS/ROWS, calculate total billed
  consumption by adding the consumption value from each relevant period.
- Example: if one period shows consumption 20.316 SCM and another shows 2.684 SCM,
  usage_amount must be 23.000 SCM. A separate "No. of days = 53" value must NOT be used.
- If multiple rows are meter adjustments, estimates, reversals, or non-consumption
  charges, do not blindly sum them. Use the values explicitly identified as
  consumption/usage.
- Use the unit associated with the consumption values.
- When the visual layout and extracted text disagree, prefer the value whose label
  and table position clearly identify it as consumption.

BILLING PERIOD RULES:
- Use the actual service/consumption period, not the invoice date or due date.
- If multiple consecutive consumption periods form one billed period, use the earliest
  consumption-period start and latest consumption-period end.
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

    # Always provide the invoice image when available. Text extraction alone can
    # destroy the spatial relationship between labels and values in invoice tables.
    user_content = [
        {
            "type": "text",
            "text": (
                "Extract the required fields from this utility invoice. "
                "Use the invoice image/layout as the primary evidence for associating "
                "labels with values, and use extracted PDF text as supporting evidence.\n\n"
                "IMPORTANT: Carefully inspect any consumption table. If there are multiple "
                "consumption periods, add the actual consumption values across those periods. "
                "Do NOT use a 'No. of days' value as usage.\n\n"
                f"EXTRACTED PDF TEXT:\n{text.strip() if text.strip() else '[No selectable text]'}"
            ),
        }
    ]

    images = (page_images or [])[:12]
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
