from wallets.electrum import launch


def test_start_invokes_venv_python_and_gui(monkeypatch):
    monkeypatch.setenv("ELECTRUM_PYTHON", "/tmp/py")
    monkeypatch.setenv("ELECTRUM_BIN", "/opt/electrum/run_electrum")
    captured = {}

    class FakeProc:
        def poll(self):
            return None

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeProc()

    monkeypatch.setattr(launch.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(launch.time, "sleep", lambda _seconds: None)
    # start() now stops any running daemon before launching the GUI; that path
    # talks to a real Electrum and is irrelevant to this test.
    monkeypatch.setattr(launch, "_ensure_no_daemon", lambda: None)

    launch.start()

    assert captured["cmd"][:2] == ["/tmp/py", "/opt/electrum/run_electrum"]
    assert "--gui" in captured["cmd"] and "qt" in captured["cmd"]
