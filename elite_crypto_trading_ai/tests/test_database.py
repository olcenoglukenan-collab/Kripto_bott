from database.store import save_scan, recent_scans

def test_scan_persistence(tmp_path):
    db = tmp_path / "test.db"
    rows = [{"symbol":"BTCUSDT", "price":65000, "direction":"LONG", "score":65, "rsi":55}]
    save_scan(rows, db)
    saved = recent_scans(5, db)
    assert len(saved) == 1
    assert saved[0][1] == "BTCUSDT"
