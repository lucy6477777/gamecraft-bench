# Hotline Heist

Build **Hotline Heist**, a top-down fast-action shooter as a Web game (HTML5 canvas / Phaser) at `/workspace/game/`.
This is not a prototype. It is a **complete, shippable micro-game** that could
sit on an itch.io page or Steam as a polished vertical slice.

## Core Vision

The fantasy is bursting through doors into rooms full of armed guards, clearing
entire floors in seconds with precise aim and brutal efficiency. The interesting
tension is fragility: both the player and enemies die in one hit, making every
room entry a lethal puzzle where hesitation means death. Combo scoring rewards
speed — chaining kills without pause multiplies the score, encouraging reckless
aggression balanced against the instant-death stakes. Weapon variety scattered
across floors forces improvisation: a shotgun clears a cluster but alerts the
next room, while a silenced pistol preserves surprise but demands accuracy.

## What the Player Experiences

The player sees a stylized title screen, selects a floor from the campaign list,
and spawns outside the building's entrance. The camera shows the full floor plan
from above — rooms, corridors, doors, and enemy patrol routes are partially
visible. The player moves with WASD, aims with the mouse, and clicks to attack.
Doors can be kicked open to stun enemies behind them.

Each floor is a self-contained puzzle of 4-8 rooms connected by doors and
hallways. Guards patrol set routes; some stand still, others pace. Weapons litter
the ground — bats, pistols, shotguns, SMGs, thrown knives — each with limited
ammo or single-use. Clearing all enemies on a floor triggers a score screen
showing time, combo chain, and weapon variety bonus. Dying restarts the floor
instantly. The campaign offers 8+ floors with escalating guard density, new enemy
types (armored, dogs, gunners), and tighter layouts.

## Assets

2D assets are mounted read-only at:

- `/workspace/assets/library/` — Kenney CC0 packs (sprites, tiles, UI, fonts).
- `/workspace/assets/library-oga/` — OpenGameArt entries; respect each
  subdir's `LICENSE.txt`.

Browse the library and choose packs.
Copy what you need into your project's `assets/` folder.

## Project layout

```
/workspace/game/
  index.html
  package.json
  src/
  public/assets/
  dist/            ← your production build, this is what gets evaluated
  demo_outputs/    ← your input traces (1–10 files)
```

The build must complete and the built page must come up cleanly:

```
cd /workspace/game && npm install && npm run build
python3 tools/web_build_check.py --project /workspace/game
```

The check serves `dist/` over a local static server and opens it in a headless
browser. It passes when three things hold: the page reaches the `load` event, a
`<canvas>` element is present, and no uncaught JavaScript error is raised during
startup. Serving matters — opening `dist/index.html` over `file://` fails on
module and asset loading and is not how the evaluator runs it.

Keep the first paint fast. Assets are decoded on the CPU here with no GPU, so a
handful of very large images can push the page past the load timeout; a build
that takes longer than 30 s to first paint is treated as a failed build.

A screenshot helper is available at `/workspace/tools/web_screenshot.py`. Use it
to actually see what your UI / play field / result screens look like.

```
python3 /workspace/tools/web_screenshot.py --project /workspace/game \
      --out /workspace/frame.png --seconds 2
```

To screenshot a specific scenario, pass `--scenario <id>`:

```
python3 /workspace/tools/web_screenshot.py --project /workspace/game \
      --out /workspace/battle_debug.png --seconds 4 --scenario battle
```

## Demos

Ship **1–10 input-trace files** under `/workspace/game/demo_outputs/`, one per
demo, each named `*.json`. The evaluator serves a fresh copy of your build per
trace, replays your trace as synthetic mouse and keyboard input at 1280×720,
and records the screen. Only the first 10 traces by filename are evaluated;
recordings longer than 20 s are sampled from a random 20 s window.

Traces are part of the deliverable, not an afterthought. A project that builds
but ships no replayable trace produces no gameplay evidence, and every
requirement that depends on observed behaviour scores 0.

### Scenarios

Normal play should start from the title screen and demonstrate the task's
core gameplay loop.
Demo playback must be deterministic. For demos that need a specific state
(a specific level, combat state, upgrade screen, result state, or late-game
setup), define named scenarios your game loads when the page is opened with a
`scenario` query parameter:

```
http://127.0.0.1:<port>/?scenario=<id>
```

When `scenario` is present the game must skip menus, set up the named state
deterministically (seed any RNG), and begin accepting input immediately.

### Coordinates

Coordinates in a trace are pixels in a **1280×720 game viewport**, measured
from the top-left of your game canvas — not from the top-left of the browser
window. The evaluator reads the canvas position and size from the page and maps
your coordinates onto it, so a canvas that is letterboxed or scaled to fit still
receives the click you intended. Author traces against your own game's
coordinate system and ignore the browser chrome.

### Trace file format

```json
{
  "scenario": "title_flow",
  "duration_frames": 360,
  "events": [
    {"frame": 30,  "type": "mouse_click", "button": "left", "x": 300, "y": 360},
    {"frame": 90,  "type": "key_press",   "keycode": "1"},
    {"frame": 180, "type": "key_press",   "keycode": "SPACE"},
    {"frame": 300, "type": "wait"}
  ]
}
```

- `scenario` — optional; omit for a normal game launch from the title screen.
- `duration_frames` — total frames to record at 30 fps; cap at **600 (20 s)**.
- `events` — time-ordered inputs. Coordinates are pixels in the 1280×720 game
  viewport (see above). Supported types:
  - `mouse_click`: `{frame, type, button: "left"|"right", x, y}`
  - `mouse_down` / `mouse_up`: `{frame, type, button: "left"|"right", x, y}` —
    use these for drag interactions: emit `mouse_down` at the start point,
    one or more `mouse_move` events along the way, and `mouse_up` at the end.
    A `mouse_click` is a `mouse_down` + `mouse_up` at the same point in tight
    succession.
  - `mouse_move`: `{frame, type, x, y}`
  - `key_press` / `key_down` / `key_up`: `{frame, type, keycode}` — keycodes:
    `A`–`Z`, `0`–`9`, `ESCAPE`, `ENTER`, `SPACE`, `TAB`, `BACKSPACE`,
    `DELETE`, `SHIFT`, `CTRL`, `ALT`, `UP`, `DOWN`, `LEFT`, `RIGHT`.

    Your game must respond to real browser keyboard events. Reading
    `event.code` (`KeyA`, `Digit1`, `Space`, `Escape`, `ArrowLeft`) is the
    reliable route; the evaluator dispatches those. A game that only listens
    for a custom in-page control will not receive these.
  - `wait`: `{frame, type}` — anchor frame, no input.

Replay must be deterministic: same trace, fresh serve, same outcome every time.
Anything time-of-day dependent, unseeded random, or reliant on network state
will not replay the same way twice and costs you the demo.
