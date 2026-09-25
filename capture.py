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
mirrors. Capturing just the emulator rectangle (with the preview parked
outside it) breaks the loop.
"""
import subprocess

import cv2
import numpy as np

from emulator import bring_to_front, find_emulator_window


def resolve_region(region, source="mss"):
    """Decide which screen rectangle to capture.

    Returns {"left","top","width","height"} or None (fullscreen / N-A).
    """
    if region:  # explicit rectangle in config.json wins
        r = dict(region)
        print(f"capturing pinned region ({r['left']},{r['top']}) "
              f"{r['width']}x{r['height']}")
        return r
    if source == "mss":
        rect = find_emulator_window()
        if rect:
            left, top, width, height = rect
            # mss sees the composited desktop: the game must be on top.
            bring_to_front()
            print(f"capturing emulator region ({left},{top}) "
                  f"{width}x{height}")
            return {"left": left, "top": top,
                    "width": width, "height": height}
        print("no emulator window found - capturing the full monitor. "
              "Open LDPlayer/BlueStacks and the game first for best results.")
    return None


def preview_position(region, screen_size, pw=640, ph=360, margin=16):
    """Top-left corner for a pw x ph preview that won't overlap `region`.

    Tries right of the region, then left, then below, then above. Falls
    back to (margin, margin) when the region covers nearly everything.
    """
    if not region or not screen_size:
        return (margin, margin)
    sw, sh = screen_size
    rl, rt = region["left"], region["top"]
    rr, rb = rl + region["width"], rt + region["height"]
    if rr + margin + pw <= sw:      # room on the right
        return (rr + margin, rt)
    if rl - margin - pw >= 0:       # room on the left
        return (rl - margin - pw, rt)
    if rb + margin + ph <= sh:      # room below
        return (rl, rb + margin)
    if rt - margin - ph >= 0:       # room above
        return (rl, rt - margin - ph)
    return (margin, margin)


def preview_to_frame(x, y, frame_w, frame_h, pw, ph):
    """Map a click in the downscaled preview back to full-res frame pixels."""
    fx = min(max(int(x * frame_w / pw), 0), frame_w - 1)
    fy = min(max(int(y * frame_h / ph), 0), frame_h - 1)
    return fx, fy


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
                cov = (self.effective_region["width"]
                       * self.effective_region["height"]) / (mon["width"] * mon["height"])
                if cov > 0.85:
                    print("WARNING: capture covers nearly the whole screen - "
                          "shrink the emulator to a smaller window so the "
                          "preview fits beside it instead of inside it.")
            else:
                print("WARNING: fullscreen capture - the preview window will "
                      "appear inside its own feed (hall of mirrors). Open the "
                      "emulator so auto-detect can lock onto it.")

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
