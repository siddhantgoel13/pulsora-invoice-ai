from datetime import date

from src.models import InvoiceData
from src.validator import validate_invoice


def test_utility_alias_normalization():
    data = InvoiceData(utility_type="Electric")
    assert data.utility_type == "electricity"


def test_valid_billing_period():
    data = InvoiceData(
        billing_period_start=date(2024, 1, 1),
        billing_period_end=date(2024, 1, 31),
    )
    _, warnings = validate_invoice(data)
    assert not any("Billing period" in w for w in warnings)


def test_invalid_billing_period():
    data = InvoiceData(
        billing_period_start=date(2024, 2, 1),
        billing_period_end=date(2024, 1, 31),
    )
    _, warnings = validate_invoice(data)
    assert any("Billing period" in w for w in warnings)


def test_low_confidence_flag():
    data = InvoiceData(confidence=0.55)
    _, warnings = validate_invoice(data)
    assert any("Low extraction confidence" in w for w in warnings)


def test_missing_unit_flag():
    data = InvoiceData(usage_amount=120)
    _, warnings = validate_invoice(data)
    assert any("usage unit" in w.lower() for w in warnings)
