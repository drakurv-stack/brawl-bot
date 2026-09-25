# Brawl Bot — learn by building a game-playing bot

A learning project: teach a script to *see* and *play* Brawl Stars on its own.
You build it in milestones, learning computer vision, real-time decision
making, and input control along the way.

## The pipeline

```
SCREEN  ->  SEE (OpenCV)  ->  THINK (state + decisions)  ->  ACT (inputs)
```

1. **Capture** (`capture.py`) — grab frames from an emulator window (fast)
   or a real phone over ADB (slow, ~2 fps).
2. **Vision** (`vision.py`) — find things on screen with HSV color masking:
   your brawler, enemies, health bars. No hardcoded magic numbers — you
   *calibrate* the colors to your own screen with `calibrate.py`.
3. **Visualize** (`visualize.py`) — live debug overlay: boxes + labels + FPS.
   If the bot can't see it here, it can't play it. This is milestone 1.
4. **Decide** (milestone 3) — turn detections into a game state, then a
   simple state machine: chase, attack, dodge, retreat.
5. **Act** (milestone 2) — drive the game with your emulator's keymapper
   (left stick -> WASD, attack -> key). Scripts send keystrokes; no
   touch-drag synthesis needed.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

For phone capture over USB: enable USB debugging, plug in, check `adb devices`.

## Milestone 1 — make it see (you are here)

```bash
# 1. Start Brawl Stars (emulator, or Training Cave on your phone)
# 2. Calibrate: click your brawler, an enemy, a health bar
python calibrate.py

# 3. Watch the bot see the game live
python visualize.py
```

`calibrate.py` keys: `1`/`2`/`3` select entity, **click** the thing on screen
to sample its color, `s` saves to `config.json`, `ESC` quits.

Capture notes: with `"region": null` (default) the camera auto-detects your
emulator window (LDPlayer / BlueStacks / Nox) and captures *only* that —
keep the emulator in front so the game is visible. Set an explicit
`{"left","top","width","height"}` in `config.json` to pin a rectangle
instead. The preview window parks itself outside the captured area so it
can't photograph itself.

## Milestones

- [x] **1. See** — capture + color calibration + live detection overlay
- [ ] **2. Move** — send WASD through the emulator keymapper, walk the Training Cave
- [ ] **3. Fight** — state machine: chase nearest enemy, attack in range, retreat at low HP
- [ ] **4. Skill** — aiming, dodging, supers, bush awareness
- [ ] **5. Learn** — replace the state machine with reinforcement learning

## Ground rules

- Train in the **Training Cave** or friendly rooms **against bots**.
- Never run this on your main account in live matches — Supercell bans bot
  accounts, and it ruins games for real players.
- This is for learning. The vision and control skills transfer to robotics,
  automation, and real CV work.
