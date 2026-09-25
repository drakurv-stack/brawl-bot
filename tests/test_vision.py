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
from vision import detect_entities  # noqa: E402


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


def main():
    scene = make_scene()
    det = detect_entities(scene, ENTITIES)
    checks = [
        ("player", det["player"], (200, 200)),
        ("enemy", det["enemy"], (450, 300)),
    ]
    ok = True
    for name, boxes, (ex, ey) in checks:
        if len(boxes) != 1:
            print(f"FAIL {name}: expected 1 box, got {len(boxes)}")
            ok = False
            continue
        b = boxes[0]
        dist = ((b["cx"] - ex) ** 2 + (b["cy"] - ey) ** 2) ** 0.5
        status = "OK " if dist < 15 else "FAIL"
        if dist >= 15:
            ok = False
        print(f"{status} {name}: box at ({b['cx']:.0f},{b['cy']:.0f}), "
              f"expected ({ex},{ey}), off by {dist:.1f}px")
    print("ALL TESTS PASSED" if ok else "TESTS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
