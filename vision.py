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
    return cv2.inRange(hsv, lower, upper)


def find_blobs(mask, min_area=200):
    """Turn a binary mask into a list of boxes, biggest first."""
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
        boxes.append({"x": x, "y": y, "w": w, "h": h, "area": area,
                      "cx": x + w / 2.0, "cy": y + h / 2.0})
    return sorted(boxes, key=lambda b: b["area"], reverse=True)


def detect_entities(bgr, entities):
    """bgr frame + entity configs -> {name: [boxes]}."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    out = {}
    for name, cfg in entities.items():
        mask = hsv_mask(hsv, cfg["hsv_lower"], cfg["hsv_upper"])
        out[name] = find_blobs(mask, cfg.get("min_area", 200))
    return out


def draw_detections(bgr, detections, entities):
    """Draw labeled boxes on a copy of the frame. Returns the annotated frame."""
    vis = bgr.copy()
    for name, boxes in detections.items():
        color = tuple(int(c) for c in entities[name].get("color", (0, 255, 0)))
        for b in boxes:
            x, y, w, h = b["x"], b["y"], b["w"], b["h"]
            cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
            cv2.putText(vis, name, (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, color, 2)
    return vis


def sample_hsv_range(hsv, cx, cy, radius=5, sigma=2.0):
    """Sample a patch around (cx, cy); return (lower, upper) HSV bounds."""
    h, w = hsv.shape[:2]
    x0, x1 = max(0, cx - radius), min(w, cx + radius + 1)
    y0, y1 = max(0, cy - radius), min(h, cy + radius + 1)
    patch = hsv[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
    mean = patch.mean(axis=0)
    std = patch.std(axis=0) + 4.0  # floor so flat colors still get a range
    lower = np.clip(mean - sigma * std, [0, 0, 0], [179, 255, 255])
    upper = np.clip(mean + sigma * std, [0, 0, 0], [179, 255, 255])
    return lower.astype(int).tolist(), upper.astype(int).tolist()
