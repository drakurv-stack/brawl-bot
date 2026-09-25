"""Tests for capture region resolution, preview placement, click mapping.

Covers the hall-of-mirrors fix: with region=null the camera must lock onto
the emulator window (not the fullscreen desktop that contains the preview),
the preview must be a small window parked outside the captured rectangle,
and clicks in the downscaled preview must map back to frame pixels.

Run:  python tests/test_capture_region.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import capture
import emulator


def check(name, cond):
    print(f"{'OK ' if cond else 'FAIL'} {name}")
    return bool(cond)


def main():
    ok = True
    real_finder = capture.find_emulator_window
    real_front = capture.bring_to_front
    capture.bring_to_front = lambda: True  # don't steal focus in tests

    # 1. explicit region in config wins, emulator ignored
    capture.find_emulator_window = lambda: (_ for _ in ()).throw(
        AssertionError("should not be called"))
    try:
        r = capture.resolve_region(
            {"left": 10, "top": 20, "width": 300, "height": 200})
        ok &= check("explicit region passes through",
                    r == {"left": 10, "top": 20, "width": 300, "height": 200})
    finally:
        capture.find_emulator_window = real_finder

    # 2. region=null + emulator open -> emulator rect (no fullscreen mirror)
    capture.find_emulator_window = lambda: (100, 50, 960, 540)
    try:
        r = capture.resolve_region(None)
        ok &= check("auto-detect uses emulator rect",
                    r == {"left": 100, "top": 50, "width": 960, "height": 540})
    finally:
        capture.find_emulator_window = real_finder

    # 3. region=null + no emulator -> fullscreen fallback (None)
    capture.find_emulator_window = lambda: None
    try:
        r = capture.resolve_region(None)
        ok &= check("no emulator falls back to fullscreen", r is None)
    finally:
        capture.find_emulator_window = real_finder
    capture.bring_to_front = real_front

    # 4. adb source ignores regions entirely
    r = capture.resolve_region(None, source="adb")
    ok &= check("adb ignores region", r is None)

    # 5. preview parks right of the region when there's room
    pos = capture.preview_position(
        {"left": 0, "top": 0, "width": 960, "height": 540},
        (1920, 1080), 640, 360)
    ok &= check("preview goes right of region", pos == (976, 0))

    # 6. no room on the right -> preview goes left of region
    pos = capture.preview_position(
        {"left": 1400, "top": 100, "width": 500, "height": 400},
        (1920, 1080), 640, 360)
    ok &= check("preview goes left of region", pos == (744, 100))

    # 7. only room below -> preview goes below region
    pos = capture.preview_position(
        {"left": 100, "top": 100, "width": 1500, "height": 400},
        (1920, 1080), 640, 360)
    ok &= check("preview goes below region", pos == (100, 516))

    # 8. fullscreen region (worst case) -> graceful fallback corner
    pos = capture.preview_position(
        {"left": 0, "top": 0, "width": 1920, "height": 1080},
        (1920, 1080), 640, 360)
    ok &= check("fullscreen region -> fallback corner", pos == (16, 16))

    # 9. no region / no screen info -> fallback corner
    ok &= check("missing info -> fallback corner",
                capture.preview_position(None, None) == (16, 16))

    # 10. click in downscaled preview maps back to frame pixels
    fx, fy = capture.preview_to_frame(320, 180, 1920, 1080, 640, 360)
    ok &= check("preview click scales to frame", (fx, fy) == (960, 540))
    fx, fy = capture.preview_to_frame(700, 400, 1920, 1080, 640, 360)
    ok &= check("click clamps to frame bounds", (fx, fy) == (1919, 1079))
    fx, fy = capture.preview_to_frame(-5, -5, 1920, 1080, 640, 360)
    ok &= check("negative click clamps to zero", (fx, fy) == (0, 0))

    # 11. emulator helpers are safe no-ops off Windows
    if sys.platform != "win32":
        ok &= check("find_emulator_window None off Windows",
                    emulator.find_emulator_window() is None)
        ok &= check("bring_to_front False off Windows",
                    emulator.bring_to_front() is False)
    else:
        print("SKIP platform no-op checks (on Windows)")

    print("ALL TESTS PASSED" if ok else "TESTS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
