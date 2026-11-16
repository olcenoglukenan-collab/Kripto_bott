import pandas as pd

def candles_frame(raw):
    cols = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
    df = pd.DataFrame(raw, columns=cols)
    for c in ("open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["close", "high", "low", "volume"])

def add_indicators(df):
    out = df.copy()
    close = out["close"]
    out["ema_fast"] = close.ewm(span=9, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=21, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100)
    rsi = rsi.mask((gain == 0) & (loss > 0), 0)
    out["rsi"] = rsi.fillna(50)
    prev = close.shift(1)
    tr = pd.concat([(out["high"] - out["low"]), (out["high"] - prev).abs(), (out["low"] - prev).abs()], axis=1).max(axis=1)
    out["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    out["volume_ratio"] = out["volume"] / out["volume"].rolling(20).mean().replace(0, float("nan"))
    return out

def analyze_symbol(symbol, raw):
    df = add_indicators(candles_frame(raw))
    if len(df) < 30:
        raise ValueError(f"{symbol}: yeterli mum verisi yok")
    last = df.iloc[-1]
    score_long = 0
    score_short = 0
    score_long += 30 if last.ema_fast > last.ema_slow else 0
    score_short += 30 if last.ema_fast < last.ema_slow else 0
    score_long += 20 if last.rsi >= 50 else 0
    score_short += 20 if last.rsi <= 50 else 0
    score_long += 20 if last.close > df.close.iloc[-6] else 0
    score_short += 20 if last.close < df.close.iloc[-6] else 0
    score_long += 15 if last.volume_ratio >= 1.2 and last.close >= last.open else 0
    score_short += 15 if last.volume_ratio >= 1.2 and last.close < last.open else 0
    direction, score = ("LONG", score_long) if score_long > score_short else (("SHORT", score_short) if score_short > score_long else ("BEKLE", 0))
    return {"symbol": symbol, "price": float(last.close), "rsi": float(last.rsi),
            "ema_fast": float(last.ema_fast), "ema_slow": float(last.ema_slow),
            "atr": float(last.atr), "volume_ratio": float(last.volume_ratio) if pd.notna(last.volume_ratio) else 0.0,
            "direction": direction if score >= 50 else "BEKLE", "score": int(score),
            "score_note": "Teknik gösterge puanı; kazanma olasılığı değildir."}
