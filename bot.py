"""Milestone 3: the brain. See -> decide -> act, every frame.

States:
  SEEK     no enemy in sight: drift toward the middle, don't camp a corner
  CHASE    enemy visible but far: run at the nearest one
  ATTACK   enemy in range: plant feet and shoot
  RETREAT  own HP low: run away from the nearest enemy

HP is estimated from your floating health bar: we remember the widest bar
seen (that's full HP) and divide. Caveat: bars change color as HP drops
(green -> red), so a bar that vanishes at low HP reads as "last known".
Milestone 5 will do this properly; for now it plays.

Ground rules: Training Cave or friendly bot rooms only. Never on your main
account in live matches.

Quit with Q or ESC in the preview window. Keys release on exit, always.
"""
import json
import time

import cv2

from capture import ScreenCapture, preview_position
from control import Controller, focus_game
from instance import single_instance
from vision import Tracker, detect_entities, draw_detections, is_above


def estimate_hp(detections, player, state):
    """HP fraction from your floating health bar width.

    Tracks the widest bar seen as 'full'. Returns last known when the bar
    isn't visible (default 1.0 = assume healthy).
    """
    bars = [b for b in detections.get("health_bar", [])
            if is_above(b, [player])]
    if bars:
        w = max(b["w"] for b in bars)
        state["full_w"] = max(state.get("full_w", 0), w)
        state["hp"] = w / state["full_w"]
    return state.get("hp", 1.0)


def decide(detections, frame_w, frame_h, state,
           attack_range=130, retreat_hp=0.35):
    """Pure decision step. Returns {"mode", "move": (dx,dy)|None, "attack"}.

    Kept pure (besides the hp-tracking state dict) so it can be unit tested
    without the game running.
    """
    players = detections.get("player", [])
    enemies = detections.get("enemy", [])
    if not players:
        return {"mode": "SEEK (no player)", "move": None, "attack": False}
    p = max(players, key=lambda b: b["area"])
    pcx, pcy = p["cx"], p["cy"]

    if enemies:
        t = min(enemies,
                key=lambda b: (b["cx"] - pcx) ** 2 + (b["cy"] - pcy) ** 2)
        dx, dy = t["cx"] - pcx, t["cy"] - pcy
        dist = (dx * dx + dy * dy) ** 0.5 or 1.0
        hp = estimate_hp(detections, p, state)
        if hp < retreat_hp:
            return {"mode": f"RETREAT (hp {hp:.0%})",
                    "move": (-dx / dist, -dy / dist), "attack": False}
        if dist <= attack_range:
            return {"mode": "ATTACK", "move": None, "attack": True}
        return {"mode": "CHASE", "move": (dx / dist, dy / dist),
                "attack": False}

    # Nobody to fight: drift to the middle instead of camping a corner.
    dx, dy = frame_w / 2 - pcx, frame_h / 2 - pcy
    dist = (dx * dx + dy * dy) ** 0.5 or 1.0
    if dist < 60:
        return {"mode": "SEEK", "move": None, "attack": False}
    return {"mode": "SEEK", "move": (dx / dist, dy / dist), "attack": False}


def main():
    single_instance("bot")
    with open("config.json") as f:
        cfg = json.load(f)
    brain = cfg.get("brain", {})
    attack_range = brain.get("attack_range_px", 130)
    retreat_hp = brain.get("retreat_hp", 0.35)
    cooldown = brain.get("attack_cooldown_s", 0.9)

    cap = ScreenCapture(cfg.get("source", "mss"), cfg.get("region"))
    print("Focusing the emulator in 3 seconds — Ctrl+C to abort...")
    for i in (3, 2, 1):
        print(f"  {i}...")
        time.sleep(1)
    focus_game()
    time.sleep(0.5)

    pw = 640
    r = cap.effective_region
    ph = max(200, int(pw * r["height"] / r["width"])) if r else 360
    name = "brawl-bot (Q to quit)"
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(name, pw, ph)
    px, py = preview_position(cap.effective_region, cap.screen_size, pw, ph)
    cv2.moveWindow(name, px, py)

    state, last_shot = {}, 0.0
    trackers = {name: Tracker() for name in cfg["entities"]}
    try:
        with Controller() as ctl:
            while True:
                frame = cap.grab()
                if frame is None:
                    print("lost the feed — quitting")
                    break
                h, w = frame.shape[:2]
                raw = detect_entities(frame, cfg["entities"])
                det = {name: trackers[name].update(boxes)
                       for name, boxes in raw.items()}
                action = decide(det, w, h, state, attack_range, retreat_hp)

                if action["move"]:
                    ctl.move(*action["move"])
                else:
                    ctl.stop()
                if action["attack"] and time.time() - last_shot > cooldown:
                    ctl.attack()
                    last_shot = time.time()

                vis = draw_detections(frame, det, cfg["entities"])
                cv2.putText(vis, f"{action['mode']}  hp~{state.get('hp', 1.0):.0%}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 255), 2)
                cv2.imshow(name, vis)
                if cv2.waitKey(30) & 0xFF in (ord("q"), 27):
                    break
    finally:
        cap.close()
        cv2.destroyAllWindows()
    print("bot stopped — keys released.")


if __name__ == "__main__":
    main()
