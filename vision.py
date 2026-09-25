"""See the game: HSV color masking -> blobs -> bounding boxes.

The core idea: every thing the bot cares about (your brawler, enemies,
health bars) has a distinctive color. Convert the frame to HSV, keep only
pixels in a calibrated color range, clean up noise, and turn the remaining
blobs into boxes with centers the decision layer can use.
"""
import cv2
import numpy as np


def hsv_mask(hsv, lower, upper):
    lower = np.array(lower, dtype=np.uint8)
    upper = np.array(upper, dtype=np.uint8)
    if lower[0] > upper[0]:
        # Hue wraps around red (e.g. 170..10): two intervals ORed together.
        m1 = cv2.inRange(hsv, lower,
                         np.array([179, upper[1], upper[2]], np.uint8))
        m2 = cv2.inRange(hsv,
                         np.array([0, lower[1], lower[2]], np.uint8), upper)
        return cv2.bitwise_or(m1, m2)
    return cv2.inRange(hsv, lower, upper)


# Shape + structural hints per entity name, merged UNDER explicit config
# (so anything here can be overridden per-entity in config.json):
#  - health bars are thin horizontal bars (min_aspect kills round bushes)...
#  - ...and they always float directly above a brawler ("above" kills bars
#    sitting on trees, water, and UI — nothing to anchor them).
# Set "above": null on the entity to disable the anchor check.
DEFAULT_SHAPES = {
    "health_bar": {"min_aspect": 2.5, "above": ["player", "enemy"]},
}


def is_above(box, anchors):
    """True if `box` floats just above one of the anchor boxes."""
    bottom = box["y"] + box["h"]
    for a in anchors:
        if abs(a["cx"] - box["cx"]) <= max(box["w"], 30):
            gap = a["y"] - bottom  # anchor's top below the bar's bottom
            if -10 <= gap <= 120:
                return True
    return False


def find_blobs(mask, min_area=200, min_aspect=None, max_aspect=None):
    """Turn a binary mask into a list of boxes, biggest first.

    min_aspect/max_aspect filter on width/height (health bars are wide).
    """
    kernel = np.ones((5, 5), np.uint8)
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(
        cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        aspect = w / max(h, 1)
        if min_aspect is not None and aspect < min_aspect:
            continue
        if max_aspect is not None and aspect > max_aspect:
            continue
        boxes.append({"x": x, "y": y, "w": w, "h": h, "area": area,
                      "cx": x + w / 2.0, "cy": y + h / 2.0})
    return sorted(boxes, key=lambda b: b["area"], reverse=True)


def detect_entities(bgr, entities):
    """bgr frame + entity configs -> {name: [boxes]}."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    cfgs = {name: {**DEFAULT_SHAPES.get(name, {}), **cfg}  # explicit wins
            for name, cfg in entities.items()}
    out = {}
    for name, cfg in cfgs.items():
        mask = hsv_mask(hsv, cfg["hsv_lower"], cfg["hsv_upper"])
        out[name] = find_blobs(mask, cfg.get("min_area", 200),
                               cfg.get("min_aspect"), cfg.get("max_aspect"))
    # Structural pass: e.g. a health bar must float above a brawler.
    for name, cfg in cfgs.items():
        above = cfg.get("above")
        if above:
            anchors = [b for n in above for b in out.get(n, [])]
            out[name] = [b for b in out[name] if is_above(b, anchors)]
    return out


def draw_detections(bgr, detections, entities):
    """Draw labeled boxes on a copy of the frame. Returns the annotated frame."""
    vis = bgr.copy()
    for name, boxes in detections.items():
        color = tuple(int(c) for c in entities[name].get("color", (0, 255, 0)))
        for b in boxes:
            # Tracker smoothing yields floats; OpenCV needs ints.
            x, y = int(b["x"]), int(b["y"])
            w, h = int(b["w"]), int(b["h"])
            label = f"{name}#{b['id']}" if "id" in b else name
            cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
            cv2.putText(vis, label, (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, color, 2)
    return vis


class Tracker:
    """Kill the shakes: remember boxes across frames.

    Raw color detection has no memory — a box flickers, jumps a few pixels,
    or vanishes for a frame whenever the mask wobbles. The tracker fixes it:
      * a box must match `min_hits` frames in a row before we report it
        (sporadic false positives never surface),
      * a track coasts through `max_misses` unmatched frames (a blink of
        occlusion doesn't kill it),
      * reported centers/sizes are an exponential moving average
        (no more jitter).

    Usage: one Tracker per entity; call update() with each frame's raw
    boxes. Returned dicts look like boxes plus an "id" that persists while
    the track lives.
    """

    def __init__(self, min_hits=3, max_misses=5, smooth=0.6, max_dist=60):
        self.min_hits = min_hits
        self.max_misses = max_misses
        self.smooth = smooth
        self.max_dist = max_dist
        self._tracks = []
        self._next_id = 0

    def update(self, boxes):
        # Greedy nearest-neighbor: each track claims its closest unmatched
        # box within max_dist.
        unmatched = list(boxes)
        for t in self._tracks:
            best, best_d = None, self.max_dist
            for b in unmatched:
                d = ((b["cx"] - t["cx"]) ** 2 + (b["cy"] - t["cy"]) ** 2) ** 0.5
                if d < best_d:
                    best, best_d = b, d
            if best is None:
                t["misses"] += 1
                continue
            unmatched.remove(best)
            s = self.smooth
            t["cx"] = s * t["cx"] + (1 - s) * best["cx"]
            t["cy"] = s * t["cy"] + (1 - s) * best["cy"]
            t["w"] = s * t["w"] + (1 - s) * best["w"]
            t["h"] = s * t["h"] + (1 - s) * best["h"]
            t["x"] = t["cx"] - t["w"] / 2
            t["y"] = t["cy"] - t["h"] / 2
            t["area"] = t["w"] * t["h"]
            t["hits"] += 1
            t["misses"] = 0
        for b in unmatched:  # leftovers start tentative tracks
            self._tracks.append({"id": self._next_id, "cx": b["cx"],
                                 "cy": b["cy"], "w": b["w"], "h": b["h"],
                                 "x": b["x"], "y": b["y"], "area": b["area"],
                                 "hits": 1, "misses": 0})
            self._next_id += 1
        self._tracks = [t for t in self._tracks
                        if t["misses"] <= self.max_misses]
        return [dict(t) for t in self._tracks if t["hits"] >= self.min_hits]


def sample_hsv_range(hsv, cx, cy, radius=5):
    """Sample a patch around (cx, cy); return (lower, upper) HSV bounds.

    Takes the MEDIAN color, not the mean: up to half the patch can be
    background (from clicking near an edge) without dragging the range off
    target. The old mean +/- std version blew up to 'match everything'
    from a single bad click. Hue wrapping around red (0/179) is
    represented as lower_h > upper_h, which hsv_mask understands.
    """
    h, w = hsv.shape[:2]
    x0, x1 = max(0, cx - radius), min(w, cx + radius + 1)
    y0, y1 = max(0, cy - radius), min(h, cy + radius + 1)
    patch = hsv[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
    med = np.median(patch, axis=0)

    HUE_PAD, SV_PAD = 10.0, 40.0
    hues = patch[:, 0]
    wraps_red = np.mean(hues < 45) > 0.2 and np.mean(hues > 135) > 0.2
    mh = float(med[0])
    if wraps_red:
        lo_h, hi_h = mh - HUE_PAD, mh + HUE_PAD
        if lo_h < 0:
            lo_h += 180  # wrap: lower > upper
        elif hi_h > 179:
            hi_h -= 180  # wrap: lower > upper
    else:
        lo_h, hi_h = mh - HUE_PAD, mh + HUE_PAD

    lower = np.array([lo_h, med[1] - SV_PAD, med[2] - SV_PAD])
    upper = np.array([hi_h, med[1] + SV_PAD, med[2] + SV_PAD])
    if lo_h <= hi_h:  # ordinary interval: keep ordered and in range
        lower = np.clip(lower, [0, 0, 0], [179, 255, 255])
        upper = np.clip(upper, [0, 0, 0], [179, 255, 255])
        upper = np.maximum(upper, lower)
    else:  # red wrap: S/V clip normally, hue keeps its lower > upper signal
        lower[1:] = np.clip(lower[1:], [0, 0], [255, 255])
        upper[1:] = np.clip(upper[1:], [0, 0], [255, 255])
        lower[0] = np.clip(lo_h, 0, 179)
        upper[0] = np.clip(hi_h, 0, 179)
    return lower.astype(int).tolist(), upper.astype(int).tolist()
