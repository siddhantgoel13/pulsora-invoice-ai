import json
import os
from datetime import date

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

Rules:
- Never invent information. Use null when a field cannot be established.
- Understand the invoice in its original language; do not require translation first.
- Normalize dates to YYYY-MM-DD.
- utility_type must be electricity, gas, or water when it can be established.
- usage_amount should represent the billed consumption, not an unrelated monetary value,
  meter reading, or rate.
- Keep the actual consumption unit, e.g. kWh, SCM, m3, gallons.
- billing_period_start/end refer to the period for which the consumption is billed.
- confidence must be between 0 and 1 and reflect confidence in the overall extraction.
"""


def parse_invoice(text: str) -> InvoiceData:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file before processing invoices."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Extract the required fields from this utility invoice text. "
                    "Use null when the evidence is insufficient.\n\n"
                    f"{text}"
                ),
            },
        ],
    )

    payload = json.loads(response.choices[0].message.content)
    return InvoiceData.model_validate(payload)
