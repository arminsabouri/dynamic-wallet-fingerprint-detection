"""Plumbing tests for the vision agent: tool dispatch and loop control. The
Anthropic client, screenshots, and the executor are all faked, so these run
with no API, no display, and no cost.
"""
import pytest
from PIL import Image

import agent as ag


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _text(t):
    return _Block(type="text", text=t)


def _tool(name, inputs, _id="t1"):
    return _Block(type="tool_use", name=name, input=inputs, id=_id)  # no .text attr


class _Resp:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class _Msgs:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def create(self, **_kw):
        self.calls += 1
        return self._responses.pop(0)


class _Client:
    def __init__(self, responses):
        self.messages = _Msgs(responses)


class _Executor:
    def __init__(self):
        self.events = []

    def click(self, x, y):
        self.events.append(("click", x, y))

    def execute(self, action):
        self.events.append(("execute", action.type))

    def type(self, text):
        self.events.append(("type", text))

    def key(self, combo):
        self.events.append(("key", combo))


class _Node:
    def __init__(self):
        self.mined = 0

    def mine_blocks(self, n=1):
        self.mined += n
        return ["aabbccddeeff0011"]


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(ag, "screenshot", lambda: Image.new("RGB", (8, 8)))
    monkeypatch.setattr(ag.anthropic, "Anthropic", lambda *a, **k: object())
    monkeypatch.setattr(ag, "X11Executor", _Executor)  # avoid real pyautogui setup
    monkeypatch.setattr(ag.time, "sleep", lambda *_a: None)


def _make(tmp_path, responses, node=None):
    a = ag.WalletAgent(node or _Node(), ag.Session(base_dir=tmp_path))
    a.client = _Client(responses)
    a.executor = _Executor()
    return a


def test_dispatches_tool_then_stops_on_end_turn(patched, tmp_path):
    node = _Node()
    a = _make(tmp_path, [
        _Resp([_tool("mine_block", {})], "tool_use"),
        _Resp([_text("all done")], "end_turn"),
    ], node=node)
    a.run()
    assert node.mined == 1                  # mine_block routed to the node
    assert a.client.messages.calls == 2     # looped once, then stopped on end_turn


def test_routes_click_to_executor(patched, tmp_path):
    a = _make(tmp_path, [
        _Resp([_tool("click", {"x": 5, "y": 7, "label": "Send"})], "tool_use"),
        _Resp([_text("done")], "end_turn"),
    ])
    a.run()
    assert ("click", 5, 7) in a.executor.events


def test_system_prompt_lists_taxonomy_slugs():
    import agent as ag
    from scenarios import taxonomy
    for t in taxonomy.TX_TYPES:
        assert t.slug in ag.SYSTEM_PROMPT, f"{t.slug} missing from SYSTEM_PROMPT"
