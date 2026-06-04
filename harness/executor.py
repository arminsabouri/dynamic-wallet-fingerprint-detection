"""Action executor abstraction.

VisionAgent produces normalized Action dicts; executors dispatch them to the
right platform API. Only X11Executor (PyAutoGUI) is implemented for now.
"""

import time
from dataclasses import dataclass
from typing import Literal


def _pg():
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    return pyautogui


@dataclass
class Action:
    type: Literal["click", "double_click", "right_click", "type", "key", "scroll", "move", "wait"]
    x: int | None = None
    y: int | None = None
    text: str | None = None
    key: str | None = None
    scroll_dy: int | None = None  # positive = up
    duration: float | None = None


class X11Executor:
    """Dispatches Action objects via PyAutoGUI on an X11 display."""

    def execute(self, action: Action) -> None:
        pg = _pg()
        match action.type:
            case "click":
                pg.click(action.x, action.y)
            case "double_click":
                pg.doubleClick(action.x, action.y)
            case "right_click":
                pg.rightClick(action.x, action.y)
            case "type":
                if action.text:
                    pg.typewrite(action.text, interval=0.04)
            case "key":
                if action.key:
                    pg.hotkey(*action.key.split("+"))
            case "scroll":
                pg.scroll(action.scroll_dy or 3, x=action.x, y=action.y)
            case "move":
                pg.moveTo(action.x, action.y, duration=0.2)
            case "wait":
                time.sleep(action.duration or 1.0)
            case _:
                raise ValueError(f"Unknown action type: {action.type}")

    def click(self, x: int, y: int) -> None:
        self.execute(Action(type="click", x=x, y=y))

    def type(self, text: str) -> None:
        self.execute(Action(type="type", text=text))

    def key(self, combo: str) -> None:
        self.execute(Action(type="key", key=combo))

    def wait(self, seconds: float) -> None:
        self.execute(Action(type="wait", duration=seconds))
