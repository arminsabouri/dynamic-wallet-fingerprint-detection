"""Screenshot capture and image-based element finding."""

import base64
import time
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def screenshot() -> Image.Image:
    import pyautogui
    return pyautogui.screenshot()


def screenshot_png_b64() -> str:
    img = screenshot()
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def find_template(
    template_path: str | Path,
    threshold: float = 0.8,
    screen: Image.Image | None = None,
) -> tuple[int, int] | None:
    """Return (x, y) center of best template match, or None if below threshold."""
    if screen is None:
        screen = screenshot()

    haystack = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
    needle = cv2.imread(str(template_path))
    if needle is None:
        raise FileNotFoundError(f"Template not found: {template_path}")

    result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    h, w = needle.shape[:2]
    cx = max_loc[0] + w // 2
    cy = max_loc[1] + h // 2
    return cx, cy


def wait_for_template(
    template_path: str | Path,
    threshold: float = 0.8,
    timeout: float = 15.0,
    poll: float = 0.5,
) -> tuple[int, int]:
    """Block until template appears; raises TimeoutError if not found."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pos = find_template(template_path, threshold)
        if pos:
            return pos
        time.sleep(poll)
    raise TimeoutError(f"Template not found within {timeout}s: {template_path}")


def save_screenshot(path: str | Path) -> None:
    screenshot().save(str(path))
