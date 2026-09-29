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

Rules:
- Never invent information. Use null when a field cannot be established.
- Read the invoice in its original language; do not require translation first.
- Normalize dates to YYYY-MM-DD.
- utility_type must be electricity, gas, or water when it can be established.
- usage_amount should represent billed consumption, not a monetary value,
  meter reading, rate, or tax amount.
- Keep the actual consumption unit, e.g. kWh, SCM, m3, gallons.
- billing_period_start/end refer to the period for which the consumption is billed.
- confidence must be between 0 and 1.
- If a value is unreadable or absent, return null instead of guessing.
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

    # Normal PDFs: use the cheaper text extraction path.
    if text.strip():
        user_content = (
            "Extract the required fields from this utility invoice text. "
            "Use null when the evidence is insufficient.\n\n"
            f"{text}"
        )
    else:
        # Scanned/image-only PDFs: let the vision-capable model read the invoice.
        # This is the important fallback for scanned utility bills.
        images = page_images or []
        # Avoid accidentally sending an extremely large document.
        images = images[:12]

        user_content = [
            {
                "type": "text",
                "text": (
                    "This PDF contains no selectable text. Inspect the invoice "
                    "page images directly and extract the required fields. "
                    "Use null when a value cannot be established. "
                    "Pay special attention to invoice date, billing period, "
                    "utility type, consumption and service address."
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
