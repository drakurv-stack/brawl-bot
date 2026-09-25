"""Milestone 2: drive the game with keystrokes.

LDPlayer translates keyboard keys into the on-screen joystick/buttons via
its keymapper (keyboard icon in the emulator's side toolbar). Set it up
once: W/A/S/D -> movement stick, and note which key you bound to Attack.

This module sends those keys. The emulator window must be focused — call
focus_game(), or run walk_test.py which does it for you.

Keys are held/released differentially: move() only presses what's new and
releases what's stale, so the stick never gets stuck down.
"""
import time

try:
    import pydirectinput as _pdi
except Exception:  # not installed, or not on Windows
    _pdi = None


def _need_backend():
    if _pdi is None:
        raise RuntimeError(
            "pydirectinput is not available — run: pip install pydirectinput "
            "(Windows only)")


def _down(key):
    _need_backend()
    _pdi.keyDown(key)


def _up(key):
    _need_backend()
    _pdi.keyUp(key)


def focus_game():
    """Bring the emulator forward so it receives our keys. Returns bool."""
    from emulator import bring_to_front
    return bring_to_front()


class Controller:
    """Sends movement/attack keys to the focused emulator window."""

    def __init__(self, up="w", down="s", left="a", right="d", attack="j"):
        self.keys = {"up": up, "down": down, "left": left, "right": right}
        self.attack_key = attack
        self._held = set()

    def _set_held(self, want):
        """Hold exactly `want` (a set of key names); release everything else."""
        for key in self._held - want:
            _up(key)
        for key in want - self._held:
            _down(key)
        self._held = set(want)

    def move(self, dx, dy, duration=None):
        """Hold the WASD combo matching a screen-space vector (x right, y down).

        dx, dy in [-1, 1]; anything under 0.3 counts as centered. With
        duration, holds that long then stops; without, holds until the next
        move()/stop() call. This is the primitive milestone 3 will steer.
        """
        want = set()
        if dx > 0.3:
            want.add(self.keys["right"])
        elif dx < -0.3:
            want.add(self.keys["left"])
        if dy > 0.3:
            want.add(self.keys["down"])
        elif dy < -0.3:
            want.add(self.keys["up"])
        self._set_held(want)
        if duration is not None:
            time.sleep(duration)
            self.stop()

    def stop(self):
        """Release every movement key."""
        self._set_held(set())

    def tap(self, key, duration=0.1):
        _down(key)
        time.sleep(duration)
        _up(key)

    def attack(self):
        """Tap whatever you bound to Attack in the emulator keymapper."""
        self.tap(self.attack_key)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()
