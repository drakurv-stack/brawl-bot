"""Grab frames from the game.

Two sources:
  - "mss": capture a region of your PC screen (use with an emulator).
    Fast (~30-60 fps). Set "region" in config.json to
    {"left":..,"top":..,"width":..,"height":..} or leave null for fullscreen.
  - "adb": pull screenshots from a real phone over USB with
    `adb exec-out screencap -p`. Slow (~2 fps) but works on hardware.
"""
import subprocess

import cv2
import numpy as np


class ScreenCapture:
    def __init__(self, source="mss", region=None):
        self.source = source
        self.region = region
        self._sct = None
        if source == "mss":
            import mss
            self._sct = mss.mss()
            mon = self._sct.monitors[1]  # primary monitor
            self._monitor = dict(mon)
            if region:
                self._monitor.update(
                    {"left": region["left"], "top": region["top"],
                     "width": region["width"], "height": region["height"]})

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
