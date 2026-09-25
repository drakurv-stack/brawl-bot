"""Interactive color calibration.

Open the live game feed, pick an entity (1/2/3...), then CLICK the thing on
screen. We sample the color under your cursor and save the HSV range to
config.json. Do this for your brawler, enemies, health bars, etc.

Keys: 1..9 select entity | click samples color | m toggles mask view
(white = what the current range catches) | s save | ESC quit
"""
import json

import cv2

from capture import ScreenCapture, preview_position, preview_to_frame
from instance import single_instance
from vision import hsv_mask, median_hsv, sample_hsv_range


def main():
    single_instance("calibrate")
    with open("config.json") as f:
        cfg = json.load(f)
    entities = cfg["entities"]
    names = list(entities.keys())
    selected = 0

    cap = ScreenCapture(cfg.get("source", "mss"), cfg.get("region"))
    state = {"frame": None}

    # Fixed small preview (aspect-matched): a 1:1 window would be as big as
    # the capture itself and could never sit outside it.
    pw = 640
    r = cap.effective_region
    ph = max(200, int(pw * r["height"] / r["width"])) if r else 360
    preview = (pw, ph)

    def on_click(event, x, y, flags, _):
        if event != cv2.EVENT_LBUTTONDOWN or state["frame"] is None:
            return
        name = names[selected]
        hsv = cv2.cvtColor(state["frame"], cv2.COLOR_BGR2HSV)
        fh, fw = hsv.shape[:2]
        fx, fy = preview_to_frame(x, y, fw, fh, pw, ph)
        lo, hi = sample_hsv_range(hsv, fx, fy)
        entities[name]["hsv_lower"] = lo
        entities[name]["hsv_upper"] = hi
        med = median_hsv(hsv, fx, fy)
        print(f"[{name}] clicked HSV ~({med[0]}, {med[1]}, {med[2]}), "
              f"range {lo} -> {hi}")
        if name == "enemy" and med[1] < 120:
            print("  ^ not vivid red — you probably missed the name text.")
            print("    click the MIDDLE of the red name above an enemy, "
                  "then press m to check.")

    cv2.namedWindow("calibrate", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("calibrate", pw, ph)
    cv2.setMouseCallback("calibrate", on_click)
    # Park the preview outside the captured region so it can't
    # photograph itself (the hall-of-mirrors bug).
    px, py = preview_position(cap.effective_region, cap.screen_size, pw, ph)
    cv2.moveWindow("calibrate", px, py)
    print("keys: 1..9 select entity | click samples | m mask view | s save | ESC quit")
    print("entities:", {i + 1: n for i, n in enumerate(names)})
    print("tip: press m after clicking — white = detected. If the whole screen")
    print("     goes white, re-click the CENTER of a solid-colored part.")
    show_mask = False

    while True:
        frame = cap.grab()
        if frame is None:
            print("no frame — is the game/emulator visible? (adb connected?)")
            break
        state["frame"] = frame
        if show_mask:
            # Show what the current click's color range actually catches.
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            ent = entities[names[selected]]
            mask = hsv_mask(hsv, ent["hsv_lower"], ent["hsv_upper"])
            vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            cv2.putText(vis, f"mask: {names[selected]}  (m=back to game)",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            vis = frame.copy()
            cv2.putText(vis, f"sampling: {names[selected]}  (m=mask, s=save, ESC=quit)",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        uncalibrated = all(
            e["hsv_lower"] == [0, 0, 0] and e["hsv_upper"] == [179, 255, 255]
            for e in entities.values())
        if uncalibrated and not show_mask:
            cv2.putText(vis, "No game visible? Open Brawl Stars FIRST, then run me.",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(vis, "Then click your brawler to teach me its color.",
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow("calibrate", vis)
        key = cv2.waitKey(30) & 0xFF
        if key == 27:
            break
        if ord("1") <= key <= ord("9"):
            idx = key - ord("1")
            if idx < len(names):
                selected = idx
                print("selected:", names[selected])
        elif key == ord("m"):
            show_mask = not show_mask
            print("mask view:", "ON — white = detected" if show_mask else "OFF")
        elif key == ord("s"):
            cfg["entities"] = entities
            with open("config.json", "w") as f:
                json.dump(cfg, f, indent=2)
            print("saved to config.json")

    cap.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
