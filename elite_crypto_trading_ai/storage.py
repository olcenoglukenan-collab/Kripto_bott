"""Stable per-user storage shared by app and worker across project updates."""
import os
from pathlib import Path
import shutil

if os.name == "nt" and os.getenv("LOCALAPPDATA"):
    DATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "ELITCryptoTradingAI" / "data"
else:
    DATA_DIR = Path.home() / ".elit_crypto_trading_ai" / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

def persistent_db(filename: str, legacy_path: Path) -> Path:
    target = DATA_DIR / filename
    if not target.exists() and legacy_path.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, target)
    return target
