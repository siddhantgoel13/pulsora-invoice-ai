import re

from .models import InvoiceData


_CURRENCY_UNIT_RE = re.compile(
    r"(?:€|\$|£|₹|₽|¥|₩|฿|₫|₴|₺|₪|₦|₱|₡|₲|₵|INR|USD|EUR|GBP|CAD|AUD|NZD|JPY|CNY|RMB|CHF|SEK|NOK|DKK|PLN|BRL|MXN|SGD|HKD)",
    re.IGNORECASE,
)

_NON_PHYSICAL_UNIT_RE = re.compile(
    r"(?:day|days|month|months|year|years|hour|hours|hr|hrs|%|percent|°[cf]|celsius|fahrenheit|temperature|account|invoice|rate|charge|cost|amount|tax)",
    re.IGNORECASE,
)


def _is_currency_unit(unit: str | None) -> bool:
    if not unit:
        return False
    return bool(_CURRENCY_UNIT_RE.search(unit.strip()))


def _is_non_physical_unit(unit: str | None) -> bool:
    if not unit:
        return False
    return bool(_NON_PHYSICAL_UNIT_RE.search(unit.strip()))


def validate_invoice(data: InvoiceData):
    warnings = []

    if data.utility_type not in {None, "electricity", "gas", "water"}:
        warnings.append(f"Unexpected utility type: {data.utility_type}")

    if data.invoice_date is None:
        warnings.append(
            "Invoice date could not be established from an explicit invoice/bill/issue date."
        )

    # Hard guardrail: usage must be a physical utility quantity, never money or
    # another non-physical metric. If the model violates this, null the field
    # rather than allowing a plausible-looking but incorrect CSV value through.
    if data.usage_amount is not None and _is_currency_unit(data.usage_unit):
        data.usage_amount = None
        data.usage_unit = None
        warnings.append(
            "Usage value appeared to be a monetary amount rather than physical utility consumption; manual review required."
        )
    elif data.usage_amount is not None and _is_non_physical_unit(data.usage_unit):
        data.usage_amount = None
        data.usage_unit = None
        warnings.append(
            "Usage value used a non-physical unit and was excluded; manual review required."
        )

    if data.usage_amount is None:
        warnings.append(
            "Utility consumption could not be established confidently; manual review required."
        )

    if data.usage_amount is not None and data.usage_amount < 0:
        warnings.append("Usage amount is negative.")

    if data.usage_amount is not None and not data.usage_unit:
        warnings.append("Usage amount exists but usage unit is missing.")

    if data.billing_period_start and data.billing_period_end:
        if data.billing_period_start > data.billing_period_end:
            warnings.append("Billing period start is after billing period end.")

    if data.invoice_date and data.billing_period_start:
        if data.billing_period_start > data.invoice_date:
            warnings.append(
                "Billing period starts after the invoice date; review the extracted dates."
            )

    if data.confidence is not None:
        if data.confidence < 0.70:
            warnings.append("Low extraction confidence; manual review required.")
        elif data.confidence < 0.90:
            warnings.append("Moderate extraction confidence; review recommended.")

    return data, warnings
