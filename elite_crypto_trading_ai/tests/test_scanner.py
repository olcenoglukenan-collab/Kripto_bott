from market_data.scanner import scan_market

class FakeClient:
    def usdt_perpetual_symbols(self):
        return [f"C{i}USDT" for i in range(240)]
    def ticker_24h(self):
        return [{"symbol": f"C{i}USDT", "quoteVolume": str(1000-i)} for i in range(240)]
    def klines(self, symbol, interval, limit):
        rows=[]
        for i in range(60):
            p=100+i*0.2
            rows.append([i, str(p), str(p+1), str(p-1), str(p+0.3), "100", i+1, "1", 1, "1", "1", "0"])
        return rows

def test_scanner_limits_universe_and_detailed_analysis():
    result=scan_market(FakeClient(), universe_size=220, analyze_top=7)
    assert result["universe_count"] == 220
    assert result["analyzed_count"] == 7
    assert len(result["universe_symbols"]) == 220
