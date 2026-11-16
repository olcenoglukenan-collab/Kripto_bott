"""Public multi-exchange trade WebSocket feeds. Read-only; never sends orders."""
import json, threading, time, sqlite3, logging
from pathlib import Path
from datetime import datetime, timezone
import websocket

ROOT = Path(__file__).resolve().parents[1]
from storage import persistent_db
DB = persistent_db('market_events.db', ROOT / 'data' / 'market_events.db')
log = logging.getLogger('elite.feeds')


def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('''CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, exchange TEXT, symbol TEXT,
            side TEXT, price REAL, qty REAL, notional REAL, event_time TEXT,
            received_at TEXT, trade_id TEXT, UNIQUE(exchange, trade_id))''')
        con.execute('''CREATE TABLE IF NOT EXISTS feed_status (
            exchange TEXT PRIMARY KEY, state TEXT, last_message TEXT, detail TEXT)''')
        con.execute('''CREATE TABLE IF NOT EXISTS whale_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, exchange TEXT, symbol TEXT,
            side TEXT, notional REAL, price REAL, event_time TEXT, threshold REAL)''')
        con.commit()


def save_status(exchange, state, detail=''):
    with sqlite3.connect(DB, timeout=10) as con:
        con.execute('''INSERT INTO feed_status(exchange,state,last_message,detail) VALUES(?,?,?,?)
          ON CONFLICT(exchange) DO UPDATE SET state=excluded.state,last_message=excluded.last_message,detail=excluded.detail''',
          (exchange, state, datetime.now(timezone.utc).isoformat(), str(detail)[:300]))
        con.commit()


def save_trade(exchange, symbol, side, price, qty, event_time, trade_id):
    if not symbol or price <= 0 or qty <= 0: return
    notional = price * qty
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB, timeout=10) as con:
        cur=con.execute('INSERT OR IGNORE INTO trades(exchange,symbol,side,price,qty,notional,event_time,received_at,trade_id) VALUES(?,?,?,?,?,?,?,?,?)',
                    (exchange, symbol, side, price, qty, notional, event_time, now, str(trade_id)))
        # Conservative, transparent threshold: $100k trade prints. This is exchange execution flow,
        # not proof of a known whale wallet or a directional position.
        if cur.rowcount and notional >= 100000:
            con.execute('INSERT INTO whale_events(exchange,symbol,side,notional,price,event_time,threshold) VALUES(?,?,?,?,?,?,?)',
                        (exchange, symbol, side, notional, price, event_time, 100000))
        con.commit()


def _ts(value):
    try: return datetime.fromtimestamp(float(value)/1000, timezone.utc).isoformat()
    except Exception: return datetime.now(timezone.utc).isoformat()


class FeedThread(threading.Thread):
    def __init__(self, exchange, url, subscribe_payloads, parser):
        super().__init__(daemon=True, name=f'ws-{exchange}')
        self.exchange, self.url = exchange, url
        self.payloads, self.parser = subscribe_payloads, parser
        self.stop_event = threading.Event()
        self.ws = None

    def stop(self):
        self.stop_event.set()
        try:
            if self.ws: self.ws.close()
        except Exception: pass

    def run(self):
        while not self.stop_event.is_set():
            try:
                save_status(self.exchange, 'BAĞLANIYOR')
                def on_open(ws):
                    save_status(self.exchange, 'BAĞLI', 'Abonelik gönderiliyor')
                    for payload in self.payloads:
                        ws.send(json.dumps(payload)); time.sleep(.15)
                def on_message(ws, message):
                    try:
                        for item in self.parser(json.loads(message)):
                            save_trade(self.exchange, *item)
                        save_status(self.exchange, 'CANLI')
                    except Exception as exc: log.debug('%s parse: %s', self.exchange, exc)
                def on_error(ws, error): save_status(self.exchange, 'HATA', error)
                def on_close(ws, code, msg): save_status(self.exchange, 'KESİLDİ', f'{code} {msg}')
                self.ws = websocket.WebSocketApp(self.url, on_open=on_open, on_message=on_message,
                                                  on_error=on_error, on_close=on_close)
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                save_status(self.exchange, 'YENİDEN BAĞLANACAK', exc)
            self.stop_event.wait(5)


def build_feeds(symbols):
    """Subscribe to a bounded liquid-symbol list. Symbols are normalized per venue."""
    feeds=[]
    # Binance USD-M aggregate trades. Combined stream supports many symbols in one socket.
    bsyms=[s.lower() for s in symbols if s.upper().endswith('USDT')][:200]
    if bsyms:
        streams='/'.join(f'{s}@aggTrade' for s in bsyms)
        def bp(msg):
            d=msg.get('data', msg)
            if 'p' not in d: return []
            return [(d.get('s',''), 'SELL' if d.get('m') else 'BUY', float(d['p']), float(d['q']), _ts(d.get('T')), d.get('a',''))]
        feeds.append(FeedThread('BINANCE', f'wss://fstream.binance.com/stream?streams={streams}', [], bp))
    # Bybit linear public trades; subscriptions split to avoid oversized messages.
    topics=[f'publicTrade.{s}' for s in bsyms]
    if topics:
        payloads=[{'op':'subscribe','args':topics[i:i+40]} for i in range(0,len(topics),40)]
        def yp(msg):
            out=[]
            for d in msg.get('data',[]) if isinstance(msg.get('data'),list) else []:
                out.append((d.get('s',''), d.get('S',''), float(d.get('p',0)), float(d.get('v',0)), _ts(d.get('T')), d.get('i','')))
            return out
        feeds.append(FeedThread('BYBIT','wss://stream.bybit.com/v5/public/linear',payloads,yp))
    # OKX spot instruments use BTC-USDT notation; size is base-asset quantity.
    inst=[s[:-4].upper()+'-USDT' for s in bsyms if s.upper().endswith('USDT')]
    if inst:
        payloads=[{'op':'subscribe','args':[{'channel':'trades','instId':x} for x in inst[i:i+50]]} for i in range(0,len(inst),50)]
        def op(msg):
            out=[]
            for d in msg.get('data',[]) if isinstance(msg.get('data'),list) else []:
                out.append((d.get('instId','').replace('-USDT','USDT'), d.get('side','').upper(), float(d.get('px',0)), float(d.get('sz',0)), _ts(d.get('ts')), d.get('tradeId','')))
            return out
        feeds.append(FeedThread('OKX','wss://ws.okx.com:8443/ws/v5/public',payloads,op))
    return feeds


def recent_data(limit=100):
    init_db()
    with sqlite3.connect(DB) as con:
        con.row_factory=sqlite3.Row
        trades=[dict(x) for x in con.execute('SELECT * FROM trades ORDER BY id DESC LIMIT ?', (limit,))]
        whales=[dict(x) for x in con.execute('SELECT * FROM whale_events ORDER BY id DESC LIMIT 50')]
        statuses=[dict(x) for x in con.execute('SELECT * FROM feed_status ORDER BY exchange')]
    return statuses, whales, trades


def latest_prices():
    init_db()
    with sqlite3.connect(DB) as con:
        rows=con.execute('''SELECT t.symbol,t.price FROM trades t JOIN (SELECT symbol,MAX(id) mid FROM trades GROUP BY symbol) x ON t.id=x.mid''').fetchall()
    return {symbol: float(price) for symbol,price in rows if price and price > 0}
