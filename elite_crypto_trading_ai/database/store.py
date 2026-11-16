import sqlite3
from pathlib import Path

from storage import persistent_db
DB_PATH = persistent_db("paper_trading.db", Path(__file__).resolve().parents[1] / "data" / "paper_trading.db")

def connect(path=DB_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, scanned_at TEXT DEFAULT CURRENT_TIMESTAMP, symbol TEXT, price REAL, direction TEXT, score INTEGER, rsi REAL)")
    con.commit()
    return con

def save_scan(rows, path=DB_PATH):
    with connect(path) as con:
        con.executemany("INSERT INTO scans(symbol, price, direction, score, rsi) VALUES(?,?,?,?,?)",
                        [(r["symbol"], r["price"], r["direction"], r["score"], r["rsi"]) for r in rows])

def recent_scans(limit=100, path=DB_PATH):
    with connect(path) as con:
        return con.execute("SELECT scanned_at, symbol, price, direction, score, rsi FROM scans ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
