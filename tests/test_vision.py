"""Synthetic test: prove the vision pipeline works without the game.

Draws a fake scene (green 'player' circle, red 'enemy' circle), runs the
detectors, and checks each is found near its true position.
Run:  python tests/test_vision.py
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vision import (detect_entities, find_blobs, hsv_mask,  # noqa: E402
                    sample_hsv_range)


def check(name, cond):
    print(f"{'OK ' if cond else 'FAIL'} {name}")
    return bool(cond)


def make_scene():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(img, (200, 200), 30, (0, 255, 0), -1)   # player: green
    cv2.circle(img, (450, 300), 25, (0, 0, 255), -1)   # enemy: red
    cv2.rectangle(img, (190, 150), (230, 160), (255, 0, 0), -1)  # distractor: blue
    return img


ENTITIES = {
    "player": {"hsv_lower": [50, 100, 100], "hsv_upper": [70, 255, 255],
               "min_area": 200},
    "enemy": {"hsv_lower": [0, 100, 100], "hsv_upper": [10, 255, 255],
              "min_area": 200},
}


def solid_hsv(h, s, v, size=11):
    """size x size patch of one HSV color."""
    return np.full((size, size, 3), (h, s, v), dtype=np.uint8)


def main():
    ok = True

    # --- original synthetic detection test ---
    scene = make_scene()
    det = detect_entities(scene, ENTITIES)
    checks = [
        ("player", det["player"], (200, 200)),
        ("enemy", det["enemy"], (450, 300)),
    ]
    for name, boxes, (ex, ey) in checks:
        if len(boxes) != 1:
            print(f"FAIL {name}: expected 1 box, got {len(boxes)}")
            ok = False
            continue
        b = boxes[0]
        dist = ((b["cx"] - ex) ** 2 + (b["cy"] - ey) ** 2) ** 0.5
        ok &= check(f"{name} box near truth (off {dist:.1f}px)", dist < 15)

    # --- sampling: solid color gives a tight range containing it ---
    lo, hi = sample_hsv_range(solid_hsv(60, 200, 200), 5, 5)
    ok &= check("solid green: hue window tight",
                0 <= hi[0] - lo[0] <= 20 and lo[0] <= 60 <= hi[0])
    ok &= check("solid green: S/V contain sample",
                lo[1] <= 200 <= hi[1] and lo[2] <= 200 <= hi[2])

    # --- sampling: edge click (30% background pixels) stays on target ---
    patch = np.full((11, 11, 3), (60, 200, 200), dtype=np.uint8)
    patch[:, 8:] = (110, 200, 200)  # ~27% blue intruders, like a bad click
    lo, hi = sample_hsv_range(patch, 5, 5)
    ok &= check("edge click: hue stays near green, not spanning to blue",
                hi[0] - lo[0] <= 40 and lo[0] <= 75)

    # --- sampling: red wrap (hues near 0 AND 179) ---
    red = np.zeros((11, 11, 3), dtype=np.uint8)
    red[:, :6, 0] = 2
    red[:, 6:, 0] = 178
    red[:, :, 1:] = 200
    lo, hi = sample_hsv_range(red, 5, 5)
    ok &= check("red wrap: lower_h > upper_h signals wrap", lo[0] > hi[0])
    mask = hsv_mask(red, lo, hi)
    ok &= check("red wrap: mask matches the red patch",
                mask.mean() > 200)
    green = solid_hsv(60, 200, 200, size=11)
    ok &= check("red wrap: mask rejects green",
                hsv_mask(green, lo, hi).mean() < 5)

    # --- aspect filter: health bars are wide, bushes are not ---
    img = np.zeros((200, 400, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 62), (255, 255, 255), -1)  # bar: 100x12
    cv2.circle(img, (300, 100), 20, (255, 255, 255), -1)          # bush: round
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = hsv_mask(hsv, [0, 0, 200], [179, 30, 255])
    bars = find_blobs(mask, min_area=100, min_aspect=2.5)
    ok &= check("aspect filter keeps the bar, drops the bush",
                len(bars) == 1 and abs(bars[0]["cx"] - 100) < 5)

    # --- detect_entities applies the health_bar shape hint by name ---
    det = detect_entities(img, {"health_bar": {"hsv_lower": [0, 0, 200],
                                               "hsv_upper": [179, 30, 255],
                                               "min_area": 100}})
    ok &= check("health_bar shape hint via detect_entities",
                len(det["health_bar"]) == 1)

    print("ALL TESTS PASSED" if ok else "TESTS FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
