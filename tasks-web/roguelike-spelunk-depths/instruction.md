# Spelunk Depths

Build **Spelunk Depths**, a procedural platformer roguelike with physics objects
and shopkeepers as a Web game (HTML5 canvas / Phaser) at `/workspace/game/`. This is not a prototype. It
is a **complete, shippable micro-game** that could sit on an itch.io page or
Steam as a polished vertical slice.

## Core Vision

An explorer descends through procedurally generated cave floors, using ropes,
bombs, and whatever objects are at hand to navigate traps, defeat creatures, and
collect treasure. Every object in the world has physics — pots can be thrown at
enemies, rocks tumble when supports are destroyed, and explosions chain through
destructible terrain. Shopkeepers sell items on certain floors but turn hostile
if the player steals. A ghost timer activates after lingering too long on any
floor, creating an invincible pursuer that forces forward progress. Shortcuts
unlock after meeting specific conditions, allowing experienced players to skip
early floors. Death is permanent and sends the player back to the surface with
nothing but knowledge.

## What the Player Experiences

A title screen shows the cave entrance with depth markers. Starting a run
places the explorer at floor 1 with basic equipment: 4 ropes and 4 bombs.

Each floor is a procedurally generated platformer level with an exit at the
bottom. The explorer runs, jumps, whips enemies, throws ropes upward to create
climbable lines, and places bombs to blast through terrain. Pots, crates, and
skulls can be picked up and thrown. Traps include arrow traps, spike pits, and
crush blocks. Enemies patrol with simple AI.

Shops appear every few floors with items for sale — buying requires gold
collected from gems and chests. Stealing triggers shopkeeper aggression for the
rest of the run. After 3 minutes on a floor, a ghost spawns and chases the
player relentlessly. Every 5 floors the environment theme changes. Death shows
a summary of depth reached, gold collected, and enemies defeated.

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
