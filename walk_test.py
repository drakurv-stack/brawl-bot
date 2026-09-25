"""Milestone 2 smoke test: walk a square in the Training Cave.

One-time setup: in LDPlayer, open the keymapper (keyboard icon in the right
toolbar) and bind W/A/S/D to the movement joystick.

Run:  python walk_test.py
"""
import time

from control import Controller, focus_game
from instance import single_instance


def main():
    single_instance("walktest")
    print("Walk test: your brawler should trace a square.")
    print("Focusing the emulator in 3 seconds — Ctrl+C to abort...")
    for i in (3, 2, 1):
        print(f"  {i}...")
        time.sleep(1)
    if not focus_game():
        print("Couldn't focus the emulator — click the LDPlayer window now.")
        time.sleep(2)
    time.sleep(0.5)

    with Controller() as ctl:  # releases all keys on exit, even on Ctrl+C
        for name, dx, dy in [("up", 0, -1), ("right", 1, 0),
                             ("down", 0, 1), ("left", -1, 0)]:
            print(f"walking {name}...")
            ctl.move(dx, dy, duration=1.0)
    print("Square complete — if Shelly traced a square, input works!")


if __name__ == "__main__":
    main()
