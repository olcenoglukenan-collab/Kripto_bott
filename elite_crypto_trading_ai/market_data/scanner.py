import os
from exchange.binance_public import BinancePublicClient
from market_data.indicators import analyze_symbol

def scan_market(client=None, universe_size=None, analyze_top=None):
    client = client or BinancePublicClient()
    universe_size = universe_size or int(os.getenv("SCAN_UNIVERSE", "220"))
    analyze_top = analyze_top or int(os.getenv("ANALYZE_TOP", "30"))
    symbols = set(client.usdt_perpetual_symbols())
    tickers = [t for t in client.ticker_24h() if t.get("symbol") in symbols]
    tickers.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
    selected = tickers[:max(1, universe_size)]
    detailed = []
    errors = []
    for ticker in selected[:max(1, min(analyze_top, len(selected)))]:
        symbol = ticker["symbol"]
        try:
            detailed.append(analyze_symbol(symbol, client.klines(symbol, "5m", 120)))
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
    detailed.sort(key=lambda r: r["score"], reverse=True)
    return {"universe_count": len(selected), "analyzed_count": len(detailed), "rows": detailed,
            "errors": errors, "universe_symbols": [t["symbol"] for t in selected]}
