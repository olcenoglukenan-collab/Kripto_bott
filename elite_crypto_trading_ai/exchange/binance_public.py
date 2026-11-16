import os
import requests

class BinancePublicClient:
    """Read-only public Binance USD-M Futures REST client; no credentials or order methods."""
    def __init__(self, base_url=None, timeout=12):
        self.base_url = (base_url or os.getenv("BINANCE_BASE_URL", "https://fapi.binance.com")).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "EliteCryptoPaper/1.0"})

    def _get(self, path, params=None):
        response = self.session.get(self.base_url + path, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get("code", 0) not in (0, "0"):
            raise RuntimeError(f"Binance API hatası: {data}")
        return data

    def usdt_perpetual_symbols(self):
        info = self._get("/fapi/v1/exchangeInfo")
        return [s["symbol"] for s in info["symbols"]
                if s.get("status") == "TRADING" and s.get("contractType") == "PERPETUAL"
                and s.get("quoteAsset") == "USDT" and s.get("symbol", "").endswith("USDT")]

    def ticker_24h(self):
        return self._get("/fapi/v1/ticker/24hr")

    def klines(self, symbol, interval="5m", limit=120):
        return self._get("/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})
