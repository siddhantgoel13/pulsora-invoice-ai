from .models import InvoiceData


def validate_invoice(data: InvoiceData):
    warnings = []

    if data.utility_type not in {None, "electricity", "gas", "water"}:
        warnings.append(f"Unexpected utility type: {data.utility_type}")

    if data.usage_amount is not None and data.usage_amount < 0:
        warnings.append("Usage amount is negative.")

    if data.billing_period_start and data.billing_period_end:
        if data.billing_period_start > data.billing_period_end:
            warnings.append("Billing period start is after billing period end.")

    if data.confidence is not None and data.confidence < 0.70:
        warnings.append("Low extraction confidence; consider manual review.")

    if data.usage_amount is not None and not data.usage_unit:
        warnings.append("Usage amount exists but usage unit is missing.")

    return data, warnings
