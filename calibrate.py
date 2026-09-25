"""Interactive color calibration.

Open the live game feed, pick an entity (1/2/3...), then CLICK the thing on
screen. We sample the color under your cursor and save the HSV range to
config.json. Do this for your brawler, enemies, health bars, etc.

Keys: 1..9 select entity | click samples color | s save | ESC quit
"""
import json

import cv2

from capture import ScreenCapture
from vision import sample_hsv_range


def main():
    with open("config.json") as f:
        cfg = json.load(f)
    entities = cfg["entities"]
    names = list(entities.keys())
    selected = 0

    cap = ScreenCapture(cfg.get("source", "mss"), cfg.get("region"))
    state = {"frame": None}

    def on_click(event, x, y, flags, _):
        if event != cv2.EVENT_LBUTTONDOWN or state["frame"] is None:
            return
        name = names[selected]
        hsv = cv2.cvtColor(state["frame"], cv2.COLOR_BGR2HSV)
        lo, hi = sample_hsv_range(hsv, x, y)
        entities[name]["hsv_lower"] = lo
        entities[name]["hsv_upper"] = hi
        print(f"[{name}] sampled HSV range {lo} -> {hi}")

    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", on_click)
    print("keys: 1..9 select entity | click samples | s save | ESC quit")
    print("entities:", {i + 1: n for i, n in enumerate(names)})

    while True:
        frame = cap.grab()
        if frame is None:
            print("no frame — is the game/emulator visible? (adb connected?)")
            break
        state["frame"] = frame
        vis = frame.copy()
        cv2.putText(vis, f"sampling: {names[selected]}  (s=save, ESC=quit)",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("calibrate", vis)
        key = cv2.waitKey(30) & 0xFF
        if key == 27:
            break
        if ord("1") <= key <= ord("9"):
            idx = key - ord("1")
            if idx < len(names):
                selected = idx
                print("selected:", names[selected])
        elif key == ord("s"):
            cfg["entities"] = entities
            with open("config.json", "w") as f:
                json.dump(cfg, f, indent=2)
            print("saved to config.json")

    cap.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
