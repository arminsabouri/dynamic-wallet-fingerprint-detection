from scenarios import electrum_driver as drv


def test_payto_builds_command(monkeypatch):
    captured = {}

    class R:
        returncode = 0
        stdout = "DEADBEEFHEX\n"
        stderr = ""

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return R()

    monkeypatch.setenv("ELECTRUM_PYTHON", "/e/py")
    monkeypatch.setenv("ELECTRUM_BIN", "/e/run_electrum")
    monkeypatch.setenv("ELECTRUM_WALLET", "/w/default_wallet")
    monkeypatch.setattr(drv.subprocess, "run", fake_run)

    out = drv.payto("bcrt1qdest", 0.005, rbf=False, feerate=5)
    assert out == "DEADBEEFHEX"
    cmd = captured["cmd"]
    assert cmd[:3] == ["/e/py", "/e/run_electrum", "--regtest"]
    assert "payto" in cmd and "bcrt1qdest" in cmd and "0.005" in cmd
    assert "--rbf" in cmd and "false" in cmd
    assert "--feerate" in cmd and "5" in cmd
    assert cmd[-2:] == ["-w", "/w/default_wallet"]


def test_broadcast_builds_command(monkeypatch):
    captured = {}

    class R:
        returncode = 0
        stdout = "thetxid\n"
        stderr = ""

    monkeypatch.setattr(drv.subprocess, "run", lambda cmd, **kw: (captured.__setitem__("cmd", cmd), R())[1])
    txid = drv.broadcast("AABBCC")
    assert txid == "thetxid"
    assert "broadcast" in captured["cmd"] and "AABBCC" in captured["cmd"]


def test_run_raises_on_error(monkeypatch):
    class R:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(drv.subprocess, "run", lambda cmd, **kw: R())
    import pytest
    with pytest.raises(RuntimeError, match="boom"):
        drv.payto("x", 1)


def test_payto_forwards_from_coins(monkeypatch):
    captured = {}

    class R:
        returncode = 0
        stdout = "HEX\n"
        stderr = ""

    monkeypatch.setattr(drv.subprocess, "run", lambda cmd, **kw: (captured.__setitem__("cmd", cmd), R())[1])
    drv.payto("dest", 0.001, from_coins="aa:0")
    # Electrum parses --from_coins as JSON (then splits on ','), so it is JSON-encoded
    assert "--from_coins" in captured["cmd"] and '"aa:0"' in captured["cmd"]


def test_paytomany_builds_json_outputs(monkeypatch):
    captured = {}

    class R:
        returncode = 0
        stdout = "HEX\n"
        stderr = ""

    monkeypatch.setattr(drv.subprocess, "run", lambda cmd, **kw: (captured.__setitem__("cmd", cmd), R())[1])
    out = drv.paytomany([("a1", 0.002), ("a2", 0.003)], rbf=False)
    assert out == "HEX"
    cmd = captured["cmd"]
    assert "paytomany" in cmd
    assert '[["a1", "0.002"], ["a2", "0.003"]]' in cmd
    assert "--rbf" in cmd and "false" in cmd


def test_listunspent_parses_json(monkeypatch):
    class R:
        returncode = 0
        stdout = '[{"prevout_hash": "aa", "prevout_n": 1, "value": "1.0"}]'
        stderr = ""

    monkeypatch.setattr(drv.subprocess, "run", lambda cmd, **kw: R())
    coins = drv.listunspent()
    assert coins[0]["prevout_hash"] == "aa" and coins[0]["prevout_n"] == 1
