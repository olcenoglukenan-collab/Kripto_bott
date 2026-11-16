"""Persistent autonomous DEMO worker. No live order endpoints or API keys."""
import os, time, logging, signal
from pathlib import Path
from dotenv import load_dotenv
from exchange.binance_public import BinancePublicClient
from market_data.scanner import scan_market
from paper_trading import open_from_signals, update_positions
from database.store import save_scan
from monitoring.feeds import build_feeds, latest_prices, save_status, init_db

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
(ROOT/'logs').mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=ROOT/'logs'/'worker.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
STOP=False

def stop(*_):
    global STOP; STOP=True

signal.signal(signal.SIGINT, stop)
if hasattr(signal,'SIGTERM'): signal.signal(signal.SIGTERM, stop)


def main():
    init_db(); client=BinancePublicClient()
    logging.info('Worker starting in PAPER mode')
    save_status('WORKER','ÇALIŞIYOR','Arka plan worker başladı; DEMO modu')
    # Universe is refreshed daily; WebSocket subscriptions reconnect automatically.
    feeds=[]; last_universe=0; last_scan=0; interval=max(20,int(os.getenv('SCAN_INTERVAL_SECONDS','60')))
    while not STOP:
        if (ROOT/'STOP_WORKER').exists():
            break
        now=time.time()
        try:
            live_prices=latest_prices()
            if live_prices:
                update_positions(live_prices)
            if now-last_universe>3600 or not feeds:
                symbols=client.usdt_perpetual_symbols()
                tickers=client.ticker_24h(); valid=set(symbols)
                tickers=[t for t in tickers if t.get('symbol') in valid]
                tickers.sort(key=lambda t:float(t.get('quoteVolume',0) or 0),reverse=True)
                selected=[t['symbol'] for t in tickers[:max(200,int(os.getenv('SCAN_UNIVERSE','220')))]]
                for f in feeds: f.stop()
                feeds=build_feeds(selected)
                for f in feeds: f.start()
                last_universe=now
                logging.info('Universe refreshed: %s symbols; feeds=%s',len(selected),len(feeds))
            if now-last_scan>=interval:
                result=scan_market(client, int(os.getenv('SCAN_UNIVERSE','220')), int(os.getenv('ANALYZE_TOP','30')))
                rows=result.get('rows',[])
                if rows: save_scan(rows)
                min_score=int(os.getenv('MIN_SIGNAL_SCORE','55'))
                opened, skipped=open_from_signals(rows, risk_pct=.005, max_positions=3, min_score=min_score)
                tickers=client.ticker_24h()
                prices={t['symbol']:float(t['lastPrice']) for t in tickers if t.get('lastPrice')}
                closed=update_positions(prices)
                detail=f"Evren={result['universe_count']}; analiz={result['analyzed_count']}; açılan={len(opened)}; kapanan={len(closed)}; açılamayan={len(skipped)}; eşik={min_score}"
                logging.info('Scan: %s | opened_details=%s | skipped_details=%s', detail, opened, skipped[:20])
                save_status('WORKER','ÇALIŞIYOR',detail)
                save_status('SCANNER','TAMAMLANDI',detail)
                last_scan=now
        except Exception as exc:
            logging.exception('Worker loop error: %s',exc)
            save_status('WORKER','HATA',str(exc))
            save_status('SCANNER','HATA',str(exc))
        time.sleep(2)
    for f in feeds: f.stop()
    save_status('WORKER','DURDURULDU')
    logging.info('Worker stopped')

if __name__=='__main__': main()
