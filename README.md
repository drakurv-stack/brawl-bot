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

Detections run through a per-entity **Tracker** (centroid tracking with
exponential moving-average smoothing): a box must persist for 3 frames
before it's believed (kills flicker), coasts through 5 missed frames, and
never jitters. Boxes are labeled `name#id` — the id sticks to the same
brawler while it's visible.

`calibrate.py` keys: `1`/`2`/`3` select entity, **click** the thing on screen
to sample its color, `m` toggles a mask view (white = detected — if the
whole screen goes white, re-click the center of a solid-colored part),
`s` saves to `config.json`, `ESC` quits.

Sampling takes the **median** color of a small patch around your click, so
up to half the patch can be background without poisoning the range. Two
tips from the trenches: click the *center* of a solid-colored area, and
for enemies sample the **red name/health bar above them** (always red)
rather than the brawler body (every brawler is a different color) — click
the middle of the red text itself. Enemies also get a gentler
noise-cleanup (`"open_ksize": 3` instead of 5) so thin red strokes survive
being mistaken for speckle; tune it per entity in config.json. Health bars
are also shape-filtered (wide and short), so bushes stop qualifying — and
a bar only counts if a brawler is detected right below it (`"above":
["player", "enemy"]`, overridable per entity, `null` disables). Color
alone can't do this: a sunlit bush and a health bar can be the same green,
but only one has a brawler underneath.

Capture notes: with `"region": null` (default) the camera auto-detects your
emulator window (LDPlayer / BlueStacks / Nox) and captures *only* that —
keep the emulator in front so the game is visible. Set an explicit
`{"left","top","width","height"}` in `config.json` to pin a rectangle
instead. The preview window parks itself outside the captured area so it
can't photograph itself.

## Milestone 2 — make it move (you are here)

One-time setup, in LDPlayer:
1. Open the keymapper (keyboard icon in the right toolbar).
2. Bind **W/A/S/D** to the movement joystick. Note which key is Attack
   (default it to `J` in `control.py` if yours differs).

Then prove the script can drive the game:

```bash
pip install -r requirements.txt   # picks up pydirectinput
python walk_test.py
```

Your brawler should trace a square in the Training Cave. `control.py` holds
the `Controller` class milestone 3 will steer: `move(dx, dy)` takes a
screen-space vector and holds the right WASD combo differentially, so keys
never get stuck down.

## Milestone 3 — the brain (built, needs a live run)

`bot.py` runs the full loop: see → decide → act, every frame.

- **SEEK**: no enemy in sight → drift to the middle, don't camp a corner
- **CHASE**: enemy far → run at the nearest one
- **ATTACK**: enemy within `attack_range_px` → plant feet and shoot
- **RETREAT**: own HP (estimated from your floating health-bar width)
  below `retreat_hp` → run away

Tune in `config.json` under `"brain"` (all optional):
`attack_range_px` (default 130), `retreat_hp` (0.35),
`attack_cooldown_s` (0.9). Bind your Attack key in the emulator keymapper
first (default `J`, change in `control.py`).

```bash
python bot.py     # Q or ESC quits; keys always release on exit
```

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
