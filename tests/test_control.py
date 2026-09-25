"""Tests for control.py key logic. No real keys are pressed: pydirectinput is
swapped for a fake recorder.

Run:  python tests/test_control.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import control


class FakePDI:
    def __init__(self):
        self.events = []

    def keyDown(self, k):
        self.events.append(("down", k))

    def keyUp(self, k):
        self.events.append(("up", k))


def check(name, cond):
    print(f"{'OK ' if cond else 'FAIL'} {name}")
    return bool(cond)


def main():
    ok = True
    fake = FakePDI()
    real = control._pdi
    control._pdi = fake
    try:
        c = control.Controller()

        c.move(1, 0)  # right
        ok &= check("right holds d", fake.events == [("down", "d")])

        c.move(1, -1)  # right + up: d stays, w added, nothing released
        ok &= check("diagonal adds w, keeps d",
                    fake.events == [("down", "d"), ("down", "w")])

        c.move(-1, 0)  # left: d and w released, a pressed
        ok &= check("direction change swaps keys",
                    sorted(fake.events) == sorted([("down", "d"), ("down", "w"),
                                                   ("down", "a"),
                                                   ("up", "d"), ("up", "w")]))

        c.move(0, 0)
        ok &= check("center releases all",
                    ("up", "a") in fake.events and c._held == set())

        fake.events.clear()
        c.move(0.1, -0.1)  # inside deadzone
        ok &= check("deadzone holds nothing",
                    fake.events == [] and c._held == set())

        fake.events.clear()
        c.tap("j", duration=0)
        ok &= check("tap presses and releases",
                    fake.events == [("down", "j"), ("up", "j")])

        fake.events.clear()
        c.move(0, -1)
        with c:  # context manager must release on exit
            pass
        ok &= check("context exit releases keys",
                    ("up", "w") in fake.events and c._held == set())

        # custom bindings are honored
        fake.events.clear()
        c2 = control.Controller(up="i", down="k", left="j", right="l")
        c2.move(0, -1)
        ok &= check("custom key bindings",
                    fake.events == [("down", "i")])
        c2.stop()

        control._pdi = None
        try:
            control.Controller().move(1, 0)
            ok &= check("missing backend raises", False)
        except RuntimeError as e:
            ok &= check("missing backend raises",
                        "pip install pydirectinput" in str(e))
    finally:
        control._pdi = real

    print("ALL TESTS PASSED" if ok else "TESTS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
