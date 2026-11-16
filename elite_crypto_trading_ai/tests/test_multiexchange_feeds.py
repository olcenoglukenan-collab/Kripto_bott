from monitoring.feeds import _ts, build_feeds

def test_timestamp_parser():
    assert _ts(1700000000000).startswith('2023-11-14')

def test_build_three_public_feeds():
    feeds=build_feeds(['BTCUSDT','ETHUSDT'])
    assert {f.exchange for f in feeds} == {'BINANCE','BYBIT','OKX'}
    assert all(f.daemon for f in feeds)

def test_large_trade_is_flagged_once(tmp_path, monkeypatch):
    import monitoring.feeds as feeds
    monkeypatch.setattr(feeds, 'DB', tmp_path / 'events.db')
    feeds.init_db()
    args=('BINANCE','BTCUSDT','BUY',50000,3,'2026-11-14T00:00:00+00:00','trade-1')
    feeds.save_trade(*args)
    feeds.save_trade(*args)  # reconnect duplicate must not duplicate whale alert
    statuses, whales, trades=feeds.recent_data()
    assert len(trades)==1
    assert len(whales)==1
    assert whales[0]['notional']==150000
