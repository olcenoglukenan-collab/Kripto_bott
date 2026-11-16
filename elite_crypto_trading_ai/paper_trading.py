"""Local-only paper trading simulator. No exchange order endpoints or credentials."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from storage import persistent_db
DB = persistent_db('paper_trading.db', Path(__file__).resolve().parent / 'data' / 'paper_trading.db')
FEE_RATE = 0.0004  # illustrative taker fee per side; funding/slippage not modeled
INITIAL_BALANCE = 100.0


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute('''CREATE TABLE IF NOT EXISTS paper_account (
        id INTEGER PRIMARY KEY CHECK(id=1), balance REAL NOT NULL, initial_balance REAL NOT NULL,
        created_at TEXT NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS paper_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, side TEXT NOT NULL,
        entry REAL NOT NULL, mark REAL NOT NULL, qty REAL NOT NULL, stop REAL NOT NULL,
        target REAL NOT NULL, entry_fee REAL NOT NULL, opened_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPEN')''')
    con.execute('''CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, side TEXT, entry REAL, exit REAL,
        qty REAL, gross_pnl REAL, fees REAL, net_pnl REAL, reason TEXT, opened_at TEXT, closed_at TEXT)''')
    row = con.execute('SELECT id FROM paper_account WHERE id=1').fetchone()
    if not row:
        con.execute('INSERT INTO paper_account VALUES(1,?,?,?)',
                    (INITIAL_BALANCE, INITIAL_BALANCE, datetime.now(timezone.utc).isoformat()))
    con.commit()
    return con


def account():
    with connect() as con:
        a = con.execute('SELECT * FROM paper_account WHERE id=1').fetchone()
        positions = [dict(r) for r in con.execute("SELECT * FROM paper_positions WHERE status='OPEN' ORDER BY id DESC")]
        trades = [dict(r) for r in con.execute('SELECT * FROM paper_trades ORDER BY id DESC LIMIT 100')]
        return dict(a), positions, trades


def open_from_signals(rows, risk_pct=0.005, max_positions=3, min_score=65):
    opened, skipped = [], []
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        balance = float(con.execute('SELECT balance FROM paper_account WHERE id=1').fetchone()[0])
        count = con.execute("SELECT COUNT(*) FROM paper_positions WHERE status='OPEN'").fetchone()[0]
        active = {r[0] for r in con.execute("SELECT symbol FROM paper_positions WHERE status='OPEN'")}
        for r in sorted(rows, key=lambda x: x.get('score', 0), reverse=True):
            if count >= max_positions:
                skipped.append('Maksimum açık pozisyon sayısına ulaşıldı')
                break
            symbol, side, entry = r['symbol'], r['direction'], float(r['price'])
            atr, score = float(r.get('atr') or 0), int(r.get('score') or 0)
            if side not in ('LONG', 'SHORT'):
                skipped.append(f'{symbol}: LONG/SHORT sinyali yok ({side})')
                continue
            if score < min_score:
                skipped.append(f'{symbol}: sinyal puanı yetersiz ({score} < {min_score})')
                continue
            if atr <= 0 or entry <= 0:
                skipped.append(f'{symbol}: ATR veya fiyat verisi geçersiz')
                continue
            if symbol in active:
                skipped.append(f'{symbol}: bu coin için zaten açık pozisyon var')
                continue
            stop_dist = atr * 1.5
            stop = entry - stop_dist if side == 'LONG' else entry + stop_dist
            target = entry + stop_dist * 2 if side == 'LONG' else entry - stop_dist * 2
            risk_cash = balance * risk_pct
            qty = min(risk_cash / stop_dist, (balance * 2.0) / entry)
            notional = qty * entry
            fee = notional * FEE_RATE
            if qty <= 0 or fee >= balance or notional < 5:
                skipped.append(f'{symbol}: bakiye/minimum sanal emir sınırı')
                continue
            balance -= fee
            con.execute('''INSERT INTO paper_positions(symbol,side,entry,mark,qty,stop,target,entry_fee,opened_at)
                           VALUES(?,?,?,?,?,?,?,?,?)''',
                        (symbol, side, entry, entry, qty, stop, target, fee, datetime.now(timezone.utc).isoformat()))
            opened.append({'symbol': symbol, 'side': side, 'entry': entry, 'qty': qty, 'stop': stop, 'target': target, 'score': score})
            active.add(symbol); count += 1
        con.execute('UPDATE paper_account SET balance=? WHERE id=1', (balance,))
        con.commit()
    return opened, skipped


def update_positions(prices):
    closed = []
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        positions = con.execute("SELECT * FROM paper_positions WHERE status='OPEN'").fetchall()
        balance = float(con.execute('SELECT balance FROM paper_account WHERE id=1').fetchone()[0])
        for p in positions:
            price = prices.get(p['symbol'])
            if price is None or price <= 0:
                continue
            side = p['side']
            reason = None
            if side == 'LONG' and price <= p['stop']: reason = 'STOP LOSS'
            elif side == 'LONG' and price >= p['target']: reason = 'TAKE PROFIT'
            elif side == 'SHORT' and price >= p['stop']: reason = 'STOP LOSS'
            elif side == 'SHORT' and price <= p['target']: reason = 'TAKE PROFIT'
            con.execute('UPDATE paper_positions SET mark=? WHERE id=?', (price, p['id']))
            if reason:
                gross = (price - p['entry']) * p['qty'] * (1 if side == 'LONG' else -1)
                exit_fee = price * p['qty'] * FEE_RATE
                net = gross - exit_fee  # entry fee was deducted at opening
                balance += gross - exit_fee
                fees = p['entry_fee'] + exit_fee
                now = datetime.now(timezone.utc).isoformat()
                con.execute("UPDATE paper_positions SET status='CLOSED', mark=? WHERE id=?", (price, p['id']))
                con.execute('''INSERT INTO paper_trades(symbol,side,entry,exit,qty,gross_pnl,fees,net_pnl,reason,opened_at,closed_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                            (p['symbol'], side, p['entry'], price, p['qty'], gross, fees, net, reason, p['opened_at'], now))
                closed.append({'symbol': p['symbol'], 'side': side, 'exit': price, 'net_pnl': net, 'reason': reason})
        con.execute('UPDATE paper_account SET balance=? WHERE id=1', (balance,))
        con.commit()
    return closed


def reset_account():
    with connect() as con:
        con.execute('DELETE FROM paper_positions')
        con.execute('DELETE FROM paper_trades')
        con.execute('UPDATE paper_account SET balance=?, initial_balance=?, created_at=? WHERE id=1',
                    (INITIAL_BALANCE, INITIAL_BALANCE, datetime.now(timezone.utc).isoformat()))
        con.commit()
