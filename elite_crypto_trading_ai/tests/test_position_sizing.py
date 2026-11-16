import pytest
from risk.position_sizing import calculate_position_size

def test_position_size_respects_risk_budget():
    result = calculate_position_size(100, 100, 99, 0.005)
    assert result["risk_budget"] == pytest.approx(0.5)
    assert result["estimated_stop_loss"] == pytest.approx(0.5)
    assert result["notional"] <= 100

def test_invalid_stop_rejected():
    with pytest.raises(ValueError):
        calculate_position_size(100, 100, 100)

def test_invalid_balance_rejected():
    with pytest.raises(ValueError):
        calculate_position_size(0, 100, 99)
