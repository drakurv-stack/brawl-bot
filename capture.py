"""Grab frames from the game.

Two sources:
  - "mss": capture the emulator window (use with LDPlayer/BlueStacks/Nox).
    Fast (~30-60 fps). Set "region" in config.json to
    {"left":..,"top":..,"width":..,"height":..} to pin a rectangle, or leave
    it null to auto-detect the emulator window. If no emulator is open we
    fall back to the full primary monitor.
  - "adb": pull screenshots from a real phone over USB with
    `adb exec-out screencap -p`. Slow (~2 fps) but works on hardware.

Why not always fullscreen? The preview window lives on the desktop, so a
fullscreen capture photographs the preview itself -> infinite hall of
mirrors. Capturing just the emulator rectangle breaks the loop.
"""
import subprocess

import cv2
import numpy as np

from emulator import find_emulator_window


def resolve_region(region, source="mss"):
    """Decide which screen rectangle to capture.

    Returns {"left","top","width","height"} or None (fullscreen / N-A).
    """
    if region:  # explicit rectangle in config.json wins
        return dict(region)
    if source == "mss":
        rect = find_emulator_window()
        if rect:
            left, top, width, height = rect
            return {"left": left, "top": top,
                    "width": width, "height": height}
        print("no emulator window found - capturing the full monitor. "
              "Open LDPlayer/BlueStacks and the game first for best results.")
    return None


def preview_position(region, screen_size, margin=24):
    """Top-left corner for an OpenCV window that won't sit inside `region`.

    Keeps the preview out of its own screenshot. Falls back to (60, 60)
    when there's nowhere sensible to put it.
    """
    if not region or not screen_size:
        return (60, 60)
    sw, sh = screen_size
    x = region["left"] + region["width"] + margin
    y = region["top"]
    if x + 320 > sw:  # no room on the right -> try below the region
        x = region["left"]
        y = region["top"] + region["height"] + margin
        if y + 200 > sh:  # no room below either -> give up gracefully
            return (60, 60)
    return (x, y)


class ScreenCapture:
    def __init__(self, source="mss", region=None):
        self.source = source
        self.effective_region = resolve_region(region, source)
        self.screen_size = None
        self._sct = None
        if source == "mss":
            import mss
            self._sct = mss.mss()
            mon = self._sct.monitors[1]  # primary monitor
            self._monitor = dict(mon)
            self.screen_size = (mon["width"], mon["height"])
            if self.effective_region:
                self._monitor.update(self.effective_region)

    def grab(self):
        """Return the current frame as a BGR numpy array, or None on failure."""
        try:
            if self.source == "mss":
                shot = self._sct.grab(self._monitor)
                return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)
            if self.source == "adb":
                out = subprocess.run(
                    ["adb", "exec-out", "screencap", "-p"],
                    capture_output=True, timeout=10)
                if out.returncode != 0:
                    return None
                return cv2.imdecode(
                    np.frombuffer(out.stdout, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return None
        raise ValueError(f"unknown source: {self.source}")

    def close(self):
        if self._sct is not None:
            self._sct.close()
