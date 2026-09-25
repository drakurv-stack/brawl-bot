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
from vision import (Tracker, detect_entities, draw_detections, find_blobs,  # noqa: E402
                    hsv_mask, sample_hsv_range)


def tbox(cx, cy, w=40, h=40):
    return {"x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
            "area": w * h, "cx": float(cx), "cy": float(cy)}


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

    # --- sampling: thin feature (red name tag) isn't drowned by background ---
    tag = np.full((11, 11, 3), (60, 60, 100), dtype=np.uint8)  # dull green bg
    tag[5:8, 1:10] = (0, 220, 220)  # thin red line, like a name tag
    lo, hi = sample_hsv_range(tag, 5, 6)  # click the middle of the line
    ok &= check("thin red line: hue window covers red",
                lo[0] <= 0 <= hi[0])
    ok &= check("thin red line: saturation window covers vivid red",
                lo[1] <= 220 <= hi[1])

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
    # (bar needs a brawler below it now, so add a player under the bar)
    cv2.circle(img, (100, 110), 20, (0, 255, 0), -1)  # player under the bar
    det = detect_entities(img, {
        "player": {"hsv_lower": [50, 100, 100], "hsv_upper": [70, 255, 255],
                   "min_area": 100},
        "health_bar": {"hsv_lower": [0, 0, 200],
                       "hsv_upper": [179, 30, 255],
                       "min_area": 100}})
    ok &= check("health_bar shape hint via detect_entities",
                len(det["health_bar"]) == 1)

    # --- anchor rule: a bar only counts above a brawler ---
    scene2 = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.circle(scene2, (200, 250), 30, (0, 255, 0), -1)      # player brawler
    cv2.rectangle(scene2, (150, 200), (250, 210), (255, 255, 255), -1)  # bar above him
    cv2.rectangle(scene2, (300, 100), (360, 108), (255, 255, 255), -1)  # bar on a "bush"
    ents = {
        "player": {"hsv_lower": [50, 100, 100], "hsv_upper": [70, 255, 255],
                   "min_area": 200},
        "health_bar": {"hsv_lower": [0, 0, 200], "hsv_upper": [179, 30, 255],
                       "min_area": 50},
    }
    det2 = detect_entities(scene2, ents)
    ok &= check("bar above brawler kept, bar on bush dropped",
                len(det2["health_bar"]) == 1
                and abs(det2["health_bar"][0]["cx"] - 200) < 5)

    # opt-out: "above": null disables the anchor check
    ents["health_bar"]["above"] = None
    det3 = detect_entities(scene2, ents)
    ok &= check('"above": null disables anchor check',
                len(det3["health_bar"]) == 2)

    # --- Tracker: flicker suppression (needs min_hits consecutive frames) ---
    tr = Tracker()
    ok &= check("tentative track not reported (1 hit)",
                tr.update([tbox(100, 100)]) == [])
    ok &= check("tentative track not reported (2 hits)",
                tr.update([tbox(102, 99)]) == [])
    out = tr.update([tbox(101, 101)])
    ok &= check("confirmed after 3 hits", len(out) == 1)

    # --- Tracker: jitter smoothing (EMA, not raw jumps) ---
    tr = Tracker(min_hits=1, smooth=0.5)
    tr.update([tbox(100, 100)])
    out = tr.update([tbox(120, 100)])  # raw jumps +20...
    ok &= check("EMA halves the jump", abs(out[0]["cx"] - 110) < 1e-9)

    # --- Tracker: coasts through brief misses, then dies ---
    tr = Tracker(min_hits=1, max_misses=2)
    tr.update([tbox(100, 100)])
    ok &= check("survives 1 missed frame", len(tr.update([])) == 1)
    ok &= check("survives 2 missed frames", len(tr.update([])) == 1)
    ok &= check("dies after 3 missed frames", tr.update([]) == [])

    # --- Tracker: two objects keep separate stable ids ---
    tr = Tracker(min_hits=2)
    tr.update([tbox(100, 100), tbox(300, 300)])
    out = tr.update([tbox(105, 102), tbox(295, 303)])
    ids = sorted(t["id"] for t in out)
    ok &= check("two tracks, stable ids", ids == [0, 1])
    left = next(t for t in out if t["id"] == 0)
    ok &= check("tracks follow their object", left["cx"] < 200)

    # --- regression: draw_detections must survive float (smoothed) boxes ---
    tr = Tracker(min_hits=1, smooth=0.5)
    tr.update([tbox(100, 100)])
    tracked = tr.update([tbox(103, 97)])  # EMA -> fractional coords
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    try:
        vis = draw_detections(frame, {"enemy": tracked},
                              {"enemy": {"color": [0, 0, 255]}})
        ok &= check("draw float tracker boxes without crashing",
                    vis.shape == frame.shape)
    except Exception as e:  # noqa: BLE001
        print(f"FAIL draw float tracker boxes without crashing ({e})")
        ok = False

    print("ALL TESTS PASSED" if ok else "TESTS FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
