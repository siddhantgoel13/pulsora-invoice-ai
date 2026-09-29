from .models import InvoiceData


def validate_invoice(data: InvoiceData):
    warnings = []

    if data.utility_type not in {None, "electricity", "gas", "water"}:
        warnings.append(f"Unexpected utility type: {data.utility_type}")

    if data.invoice_date is None:
        warnings.append(
            "Invoice/bill date could not be confidently identified. "
            "Due date must not be used as invoice date."
        )

    if data.usage_amount is None:
        warnings.append(
            "Utility consumption could not be confidently identified. "
            "Billing days and meter readings must not be used as usage."
        )

    if data.usage_amount is not None and data.usage_amount < 0:
        warnings.append("Usage amount is negative.")

    if data.usage_amount is not None and not data.usage_unit:
        warnings.append("Usage amount exists but usage unit is missing.")

    if data.billing_period_start and data.billing_period_end:
        if data.billing_period_start > data.billing_period_end:
            warnings.append("Billing period start is after billing period end.")

    if data.confidence is not None:
        if data.confidence < 0.70:
            warnings.append("Low extraction confidence; manual review required.")
        elif data.confidence < 0.90:
            warnings.append("Moderate extraction confidence; review recommended.")

    return data, warnings
