from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InvoiceData(BaseModel):
    vendor_name: Optional[str] = None
    invoice_date: Optional[date] = None
    service_address: Optional[str] = None
    utility_type: Optional[str] = None
    usage_amount: Optional[float] = None
    usage_unit: Optional[str] = None
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

    @field_validator("utility_type")
    @classmethod
    def normalize_utility_type(cls, value):
        if value is None:
            return value
        v = value.strip().lower()
        aliases = {
            "electric": "electricity",
            "electricity": "electricity",
            "power": "electricity",
            "gas": "gas",
            "natural gas": "gas",
            "water": "water",
        }
        return aliases.get(v, v)
