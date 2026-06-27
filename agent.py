"""Autonomous wallet enumeration agent.

Drives the Electrum GUI via Claude Vision + tool_use to discover and execute
every possible transaction type. The agent reasons about what it has tried,
what remains, and decides its own next steps.
"""

import base64
import json
import os
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import anthropic
from PIL import Image

from harness.executor import Action, X11Executor
from harness.screen import screenshot
from bitcoin.regtest import RegtestNode
from wallets.electrum.setup import get_wallet_address
from scenarios.taxonomy import enumeration_checklist

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""\
You are an autonomous Bitcoin wallet testing agent running on a Linux desktop.

MISSION: Systematically enumerate EVERY type of Bitcoin transaction that can \
be created using the Electrum wallet GUI. You decide what to try — explore \
the interface, read menus, discover options, and attempt every transaction \
variant you can find.

ENVIRONMENT:
- Electrum Bitcoin wallet (Qt desktop app) connected to local Bitcoin regtest
- You have unlimited free Bitcoin — call get_coins whenever the wallet balance is low
- All transactions are on regtest (fake network, safe to experiment freely)

TRANSACTION TYPES TO COVER (each exercises a distinct wallet fingerprint):
{enumeration_checklist()}
Discover and attempt any additional variant the wallet UI exposes beyond this list.

HOW TO OPERATE:
1. Call log_decision BEFORE attempting each new transaction type — describe \
   what you're trying and which fingerprint signal it exercises. Use the slug \
   above as transaction_type when it matches.
2. Take a screenshot whenever you need to see the current UI state
3. Navigate by clicking, typing, and using keyboard shortcuts
4. After broadcasting a transaction, mine a block to confirm it
5. Explore ALL menus: Wallet menu, Tools menu, right-click context menus on \
   transactions and UTXOs, the Coins tab, advanced dialogs
6. Keep track of what you've already successfully executed
7. When you are confident you have covered every reachable transaction type, \
   output a final summary and stop (don't call any more tools)

REGTEST ADDRESSES TO USE AS RECIPIENTS:
When you need an external recipient address, use these (they belong to the \
regtest Bitcoin Core node, not the wallet):
- P2PKH (legacy): use the get_external_address tool with type "legacy"
- P2WPKH (bech32): use get_external_address with type "bech32"
- P2SH: use get_external_address with type "p2sh-segwit"
- P2TR (taproot): use get_external_address with type "bech32m"

IMPORTANT: Log every decision. The log is the primary output of this run.
"""

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "screenshot",
        "description": "Capture the current state of the wallet GUI. Returns an image of the screen.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "click",
        "description": "Click at pixel coordinates (x, y) on screen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "label": {"type": "string", "description": "Human-readable label of what you're clicking (for logs)"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "double_click",
        "description": "Double-click at pixel coordinates (x, y).",
        "input_schema": {
            "type": "object",
            "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
            "required": ["x", "y"],
        },
    },
    {
        "name": "right_click",
        "description": "Right-click at (x, y) to open a context menu.",
        "input_schema": {
            "type": "object",
            "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
            "required": ["x", "y"],
        },
    },
    {
        "name": "type_text",
        "description": "Type text into the currently focused input field.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "press_key",
        "description": "Press a key or keyboard combo. Examples: 'Tab', 'Enter', 'Escape', 'ctrl+a', 'ctrl+c', 'Delete'.",
        "input_schema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
    {
        "name": "scroll",
        "description": "Scroll the mouse wheel at position (x, y).",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "direction": {"type": "string", "enum": ["up", "down"]},
                "clicks": {"type": "integer", "description": "Number of scroll steps (default 3)"},
            },
            "required": ["x", "y", "direction"],
        },
    },
    {
        "name": "get_coins",
        "description": "Request free Bitcoin from the regtest faucet. Sends BTC to the wallet and mines a confirming block. Use whenever the wallet balance is insufficient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount_btc": {"type": "number", "description": "Amount in BTC (e.g. 1.0)"},
            },
            "required": ["amount_btc"],
        },
    },
    {
        "name": "get_external_address",
        "description": "Get a fresh Bitcoin address from the regtest node (not the wallet) to use as a transaction recipient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "addr_type": {
                    "type": "string",
                    "enum": ["bech32", "legacy", "p2sh-segwit", "bech32m"],
                    "description": "Address type: bech32=P2WPKH, legacy=P2PKH, p2sh-segwit=P2SH, bech32m=P2TR",
                },
            },
            "required": ["addr_type"],
        },
    },
    {
        "name": "mine_block",
        "description": "Mine one regtest block to confirm pending transactions in the mempool.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "wait",
        "description": "Pause execution for a number of seconds (e.g. for UI to load).",
        "input_schema": {
            "type": "object",
            "properties": {"seconds": {"type": "number"}},
            "required": ["seconds"],
        },
    },
    {
        "name": "log_decision",
        "description": (
            "Record a reasoning decision before attempting a new transaction type. "
            "Call this every time you decide to try something new. "
            "This is the primary structured output of the enumeration."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_type": {
                    "type": "string",
                    "description": "Short slug for this tx type, e.g. 'simple_send_p2wpkh', 'rbf_bump', 'send_max'",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why you're attempting this, what fingerprint signal it exercises, and how you'll do it",
                },
                "already_completed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Slugs of transaction types you have already successfully completed",
                },
            },
            "required": ["transaction_type", "reasoning"],
        },
    },
]

# ---------------------------------------------------------------------------
# Session logger
# ---------------------------------------------------------------------------

class Session:
    def __init__(self, base_dir: Path = Path("logs")):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.dir = base_dir / f"session_{ts}"
        self.shots_dir = self.dir / "screenshots"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "session.jsonl"
        self._step = 0
        self.log({"type": "session_start", "session_dir": str(self.dir)})
        print(f"Session log: {self.log_path}")

    def log(self, event: dict) -> None:
        record = {
            "step": self._step,
            "ts": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        with self.log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")
        self._step += 1

    def save_screenshot(self, img: Image.Image) -> Path:
        path = self.shots_dir / f"step_{self._step:04d}.jpg"
        # Resize to 1280x800 max, JPEG for token efficiency
        img.thumbnail((1280, 800), Image.LANCZOS)
        img.save(str(path), "JPEG", quality=80)
        return path

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class WalletAgent:

    def __init__(self, node: RegtestNode, session: Session):
        self.node = node
        self.session = session
        self.executor = X11Executor()
        self.client = anthropic.Anthropic()
        self._messages: list[dict] = []

    def run(self) -> None:
        # Kick off with an initial screenshot so Claude sees the UI
        img = screenshot()
        initial_img_block = self._encode_screenshot(img)
        self.session.save_screenshot(img)
        self.session.log({"type": "screenshot", "note": "initial"})

        self._messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Electrum wallet is running. Here is the current state:"},
                    initial_img_block,
                    {"type": "text", "text": "Begin your systematic enumeration of all possible Bitcoin transactions."},
                ],
            }
        ]

        step = 0
        while True:
            step += 1
            print(f"\n--- Agent step {step} ---")

            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self._trimmed_messages(),
            )

            # Log any text the agent emits
            for block in response.content:
                if hasattr(block, "text"):
                    self.session.log({"type": "agent_text", "text": block.text})
                    if block.text.strip():
                        print(f"[Agent] {block.text.strip()[:200]}")

            self._messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                print("\nAgent completed enumeration.")
                self.session.log({"type": "session_end", "reason": "agent_stopped"})
                break

            if response.stop_reason != "tool_use":
                print(f"Unexpected stop: {response.stop_reason}")
                self.session.log({"type": "session_end", "reason": response.stop_reason})
                break

            # Execute all tool calls in this turn
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_content = self._execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_content,
                    })

            self._messages.append({"role": "user", "content": tool_results})

    # -- Tool execution --

    def _execute_tool(self, name: str, inputs: dict) -> list[dict]:
        self.session.log({"type": "tool_call", "tool": name, "inputs": inputs})
        print(f"  [{name}] {json.dumps(inputs)[:120]}")

        try:
            return self._dispatch(name, inputs)
        except Exception as exc:
            self.session.log({"type": "tool_error", "tool": name, "error": str(exc)})
            print(f"  ERROR: {exc}")
            return [{"type": "text", "text": f"Error executing {name}: {exc}"}]

    def _dispatch(self, name: str, inputs: dict) -> list[dict]:
        if name == "screenshot":
            img = screenshot()
            path = self.session.save_screenshot(img)
            self.session.log({"type": "screenshot", "path": str(path)})
            return [
                {"type": "text", "text": "Screenshot captured."},
                self._encode_screenshot(img),
            ]

        elif name == "click":
            self.executor.click(inputs["x"], inputs["y"])
            time.sleep(0.35)
            return [{"type": "text", "text": f"Clicked ({inputs['x']}, {inputs['y']}) — {inputs.get('label', '')}"}]

        elif name == "double_click":
            self.executor.execute(Action(type="double_click", x=inputs["x"], y=inputs["y"]))
            time.sleep(0.35)
            return [{"type": "text", "text": f"Double-clicked ({inputs['x']}, {inputs['y']})"}]

        elif name == "right_click":
            self.executor.execute(Action(type="right_click", x=inputs["x"], y=inputs["y"]))
            time.sleep(0.35)
            return [{"type": "text", "text": f"Right-clicked ({inputs['x']}, {inputs['y']})"}]

        elif name == "type_text":
            self.executor.type(inputs["text"])
            return [{"type": "text", "text": f"Typed: {inputs['text'][:80]}"}]

        elif name == "press_key":
            self.executor.key(inputs["key"])
            time.sleep(0.2)
            return [{"type": "text", "text": f"Pressed: {inputs['key']}"}]

        elif name == "scroll":
            dy = (inputs.get("clicks") or 3) * (1 if inputs["direction"] == "up" else -1)
            self.executor.execute(Action(type="scroll", x=inputs["x"], y=inputs["y"], scroll_dy=dy))
            return [{"type": "text", "text": f"Scrolled {inputs['direction']} at ({inputs['x']}, {inputs['y']})"}]

        elif name == "get_coins":
            addr = get_wallet_address()
            txid = self.node.fund_address(addr, inputs["amount_btc"])
            self.node.mine_blocks(1)
            time.sleep(2.5)  # Fulcrum indexing
            return [{"type": "text", "text": f"Sent {inputs['amount_btc']} BTC to {addr}. Confirmed. txid={txid[:16]}..."}]

        elif name == "get_external_address":
            addr = self.node.get_new_address(addr_type=inputs["addr_type"])
            return [{"type": "text", "text": addr}]

        elif name == "mine_block":
            blocks = self.node.mine_blocks(1)
            time.sleep(2.5)
            return [{"type": "text", "text": f"Block mined: {blocks[0][:16]}..."}]

        elif name == "wait":
            time.sleep(float(inputs["seconds"]))
            return [{"type": "text", "text": f"Waited {inputs['seconds']}s"}]

        elif name == "log_decision":
            self.session.log({
                "type": "decision",
                "transaction_type": inputs["transaction_type"],
                "reasoning": inputs["reasoning"],
                "already_completed": inputs.get("already_completed", []),
            })
            print(f"\n  *** DECISION: {inputs['transaction_type']}")
            print(f"      {inputs['reasoning'][:120]}")
            return [{"type": "text", "text": f"Decision logged: {inputs['transaction_type']}"}]

        else:
            return [{"type": "text", "text": f"Unknown tool: {name}"}]

    # -- Screenshot encoding --

    def _encode_screenshot(self, img: Image.Image) -> dict:
        img = img.copy()
        img.thumbnail((1280, 800), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        }

    # -- Context trimming: keep only the last 2 screenshots in the message history --

    def _trimmed_messages(self) -> list[dict]:
        result = []
        images_kept = 0
        max_images = 2

        for msg in reversed(self._messages):
            if msg["role"] == "user" and isinstance(msg["content"], list):
                new_content = []
                for block in msg["content"]:
                    if isinstance(block, dict):
                        if block.get("type") == "image":
                            if images_kept < max_images:
                                images_kept += 1
                                new_content.append(block)
                            # else: drop old screenshot from context
                        elif block.get("type") == "tool_result":
                            content = block.get("content", [])
                            if isinstance(content, list):
                                has_img = any(c.get("type") == "image" for c in content)
                                if has_img:
                                    if images_kept < max_images:
                                        images_kept += 1
                                        new_content.append(block)
                                    else:
                                        text_only = [c for c in content if c.get("type") != "image"]
                                        new_content.append({**block, "content": text_only})
                                else:
                                    new_content.append(block)
                            else:
                                new_content.append(block)
                        else:
                            new_content.append(block)
                    else:
                        new_content.append(block)
                result.append({**msg, "content": new_content})
            else:
                result.append(msg)

        return list(reversed(result))
