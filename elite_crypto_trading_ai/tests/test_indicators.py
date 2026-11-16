from market_data.indicators import analyze_symbol

def make_candles(n=60):
    rows = []
    for i in range(n):
        p = 100 + i * 0.5
        rows.append([i, str(p), str(p + 1), str(p - 1), str(p + 0.5), "100", i+1, "10000", 10, "60", "6000", "0"])
    return rows

def test_analysis_returns_valid_signal_shape():
    result = analyze_symbol("TESTUSDT", make_candles())
    assert result["symbol"] == "TESTUSDT"
    assert result["direction"] in {"LONG", "SHORT", "BEKLE"}
    assert 0 <= result["score"] <= 100
    assert result["price"] > 0
