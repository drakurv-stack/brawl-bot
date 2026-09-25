"""Tests for capture region resolution + preview placement.

Covers the hall-of-mirrors fix: with region=null the camera must lock onto
the emulator window (not the fullscreen desktop that contains the preview),
and the preview window must be parked outside the captured rectangle.

Run:  python tests/test_capture_region.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import capture
import emulator


def check(name, cond):
    print(f"{'OK ' if cond else 'FAIL'} {name}")
    return cond


def main():
    ok = True
    real_finder = capture.find_emulator_window

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

    # 4. adb source ignores regions entirely
    r = capture.resolve_region(None, source="adb")
    ok &= check("adb ignores region", r is None)

    # 5. preview parks right of the region when there's room
    pos = capture.preview_position(
        {"left": 0, "top": 0, "width": 960, "height": 540}, (1920, 1080))
    ok &= check("preview goes right of region", pos == (984, 0))

    # 6. region hugging the right edge -> preview goes below it
    pos = capture.preview_position(
        {"left": 1400, "top": 100, "width": 500, "height": 400}, (1920, 1080))
    ok &= check("preview goes below region", pos == (1400, 524))

    # 7. fullscreen region (worst case) -> graceful fallback corner
    pos = capture.preview_position(
        {"left": 0, "top": 0, "width": 1920, "height": 1080}, (1920, 1080))
    ok &= check("fullscreen region -> fallback corner", pos == (60, 60))

    # 8. no region / no screen info -> fallback corner
    ok &= check("missing info -> fallback corner",
                capture.preview_position(None, None) == (60, 60))

    # 9. emulator finder is a safe no-op off Windows
    if sys.platform != "win32":
        ok &= check("find_emulator_window None off Windows",
                    emulator.find_emulator_window() is None)
    else:
        print("SKIP find_emulator_window platform check (on Windows)")

    print("ALL TESTS PASSED" if ok else "TESTS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
