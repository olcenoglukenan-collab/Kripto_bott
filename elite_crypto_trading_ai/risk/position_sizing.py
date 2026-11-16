def calculate_position_size(balance, entry, stop, risk_fraction=0.005, max_notional_fraction=1.0):
    """Return base-asset quantity. Leverage is deliberately not used to inflate risk."""
    values = (balance, entry, stop, risk_fraction, max_notional_fraction)
    if any(v is None for v in values) or balance <= 0 or entry <= 0 or stop <= 0:
        raise ValueError("Bakiye, giriş ve stop pozitif olmalı")
    distance = abs(entry - stop)
    if distance <= 0:
        raise ValueError("Stop fiyatı girişten farklı olmalı")
    risk_budget = balance * risk_fraction
    qty_by_risk = risk_budget / distance
    qty_by_notional = (balance * max_notional_fraction) / entry
    qty = min(qty_by_risk, qty_by_notional)
    return {"quantity": qty, "risk_budget": risk_budget, "notional": qty * entry,
            "estimated_stop_loss": qty * distance}
