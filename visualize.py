"""Milestone 1: live detection overlay.

Captures the game, runs every calibrated entity detector, and draws boxes.
If the bot can see it here, it can play it. Press Q to quit.
"""
import json
import time

import cv2

from capture import ScreenCapture
from instance import single_instance
from vision import detect_entities, draw_detections


def main():
    single_instance("visualize")
    with open("config.json") as f:
        cfg = json.load(f)
    entities = cfg["entities"]

    cap = ScreenCapture(cfg.get("source", "mss"), cfg.get("region"))
    prev = time.time()
    while True:
        frame = cap.grab()
        if frame is None:
            print("no frame — is the game/emulator visible?")
            break
        detections = detect_entities(frame, entities)
        vis = draw_detections(frame, detections, entities)

        now = time.time()
        fps = 1.0 / max(now - prev, 1e-6)
        prev = now
        counts = "  ".join(f"{n}:{len(b)}" for n, b in detections.items())
        cv2.putText(vis, f"{fps:.0f} fps  {counts}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow("brawl-bot vision (Q to quit)", vis)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
