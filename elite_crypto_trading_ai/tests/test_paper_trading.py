import paper_trading as pt


def test_open_and_take_profit(tmp_path, monkeypatch):
    monkeypatch.setattr(pt, 'DB', tmp_path / 'paper.db')
    rows = [{'symbol':'BTCUSDT','direction':'LONG','price':100.0,'atr':2.0,'score':80}]
    opened, _ = pt.open_from_signals(rows, risk_pct=0.005, max_positions=2, min_score=65)
    assert len(opened) == 1
    acc, positions, _ = pt.account()
    assert len(positions) == 1
    assert acc['balance'] < 100.0
    # Target is entry + 2 * (1.5 ATR) = 106.
    closed = pt.update_positions({'BTCUSDT': 106.1})
    assert len(closed) == 1
    acc, positions, trades = pt.account()
    assert not positions
    assert len(trades) == 1
    assert trades[0]['net_pnl'] > 0


def test_short_stop_loss(tmp_path, monkeypatch):
    monkeypatch.setattr(pt, 'DB', tmp_path / 'paper.db')
    rows = [{'symbol':'ETHUSDT','direction':'SHORT','price':100.0,'atr':2.0,'score':75}]
    opened, _ = pt.open_from_signals(rows)
    assert len(opened) == 1
    closed = pt.update_positions({'ETHUSDT': 103.1})
    assert len(closed) == 1
    assert closed[0]['reason'] == 'STOP LOSS'
