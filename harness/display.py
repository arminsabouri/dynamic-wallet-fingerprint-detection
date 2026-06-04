"""Xvfb virtual display management."""

import os
from xvfbwrapper import Xvfb

_vdisplay: Xvfb | None = None


def start(width: int = 1280, height: int = 800) -> str:
    """Start a virtual X display. Returns the DISPLAY string (e.g. ':1')."""
    global _vdisplay
    if os.getenv("DWF_DEBUG_DISPLAY", "0") == "1":
        return os.environ.get("DISPLAY", ":0")

    _vdisplay = Xvfb(width=width, height=height, colordepth=24)
    _vdisplay.start()
    display = f":{_vdisplay.vdisplay_num}"
    os.environ["DISPLAY"] = display
    return display


def stop() -> None:
    global _vdisplay
    if _vdisplay:
        _vdisplay.stop()
        _vdisplay = None
