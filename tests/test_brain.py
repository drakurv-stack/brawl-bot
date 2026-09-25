"""Tests for the Milestone 3 brain: decide() with synthetic detections.

No game, no keys — pure logic. Run:  python tests/test_brain.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import decide, estimate_hp  # noqa: E402


def box(cx, cy, w=40, h=40):
    return {"x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h,
            "area": w * h, "cx": cx, "cy": cy}


def bar_above(player, w=60):
    # health bar floating right above the player, like the real game
    return box(player["cx"], player["y"] - 15, w=w, h=10)


def check(name, cond):
    print(f"{'OK ' if cond else 'FAIL'} {name}")
    return bool(cond)


def main():
    ok = True
    W, H = 640, 480

    # 1. no player visible -> don't move blind
    a = decide({"enemy": [box(400, 300)]}, W, H, {})
    ok &= check("no player -> stop", a["move"] is None and not a["attack"])

    # 2. enemy far -> chase toward it
    p = box(100, 100)
    a = decide({"player": [p], "enemy": [box(400, 300)]}, W, H, {})
    ok &= check("far enemy -> CHASE", a["mode"] == "CHASE")
    dx, dy = a["move"]
    ok &= check("chase vector points at enemy", dx > 0.3 and dy > 0.3)

    # 3. nearest of several enemies is picked
    a = decide({"player": [p], "enemy": [box(500, 400), box(300, 200)]},
               W, H, {})
    dx, dy = a["move"]
    ok &= check("nearest enemy chosen", a["mode"] == "CHASE"
                and dx > 0.3 and dy > 0.3
                and abs(dx) > abs(dy))  # (300,200) is mostly +x away

    # 4. enemy in range -> plant feet and shoot
    a = decide({"player": [p], "enemy": [box(150, 120)]}, W, H, {},
               attack_range=130)
    ok &= check("close enemy -> ATTACK",
                a["mode"] == "ATTACK" and a["move"] is None and a["attack"])

    # 5. low hp -> retreat away from enemy
    state = {}
    det = {"player": [p], "enemy": [box(400, 300)],
           "health_bar": [bar_above(p, w=60)]}
    decide(det, W, H, state)  # first sighting: full hp bar, full_w = 60
    det["health_bar"] = [bar_above(p, w=15)]  # bar shrank to 25%
    a = decide(det, W, H, state, retreat_hp=0.35)
    ok &= check("low hp -> RETREAT", a["mode"].startswith("RETREAT"))
    dx, dy = a["move"]
    ok &= check("retreat vector points away", dx < -0.3 and dy < -0.3)

    # 6. hp estimator remembers last known when bar vanishes
    hp = estimate_hp({"player": [p], "health_bar": []}, p, state)
    ok &= check("hp persists without bar", abs(hp - 0.25) < 1e-9)

    # 7. no enemies -> drift to center
    a = decide({"player": [box(50, 50)]}, W, H, {})
    ok &= check("no enemy -> SEEK", a["mode"] == "SEEK")
    dx, dy = a["move"]
    ok &= check("seek drifts to middle", dx > 0.3 and dy > 0.3)

    # 8. already near center -> hold still
    a = decide({"player": [box(W / 2, H / 2)]}, W, H, {})
    ok &= check("centered -> hold", a["move"] is None)

    # 9. biggest player box wins (two detections of you)
    a = decide({"player": [box(100, 100, 20, 20), box(100, 100)],
                "enemy": [box(400, 300)]}, W, H, {})
    ok &= check("uses biggest player box", a["mode"] == "CHASE")

    print("ALL TESTS PASSED" if ok else "TESTS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
