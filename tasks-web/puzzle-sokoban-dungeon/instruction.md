# Sokoban Dungeon

Build **Sokoban Dungeon**, a 2D turn-based crate-pushing dungeon puzzle as a Web game (HTML5 canvas / Phaser) at `/workspace/game/`. The player pushes crates through procedurally
generated dungeon rooms while enemies move simultaneously on each turn,
collecting keys and items to unlock deeper floors.

This is not a prototype. It is a **complete, shippable micro-game** that could
sit on an itch.io page or Steam as a polished vertical slice.

## Core Vision

The game is a turn-based puzzle-roguelike hybrid where every player step
triggers an enemy step. Each dungeon room is a spatial puzzle: crates must be
pushed onto pressure plates to open doors, but enemies patrol the grid and
move toward the player whenever the player moves. The tension comes from the
simultaneous-turn system — pushing a crate takes a turn, during which enemies
close in, so the player must solve spatial puzzles under mounting threat. Keys
unlock new rooms, items provide one-use abilities (freeze enemies, pull crates,
teleport), and procedural room layouts ensure variety. The best version feels
like chess merged with a warehouse puzzle, where every move has tactical
consequences.

## What the Player Experiences

A title screen sets the dungeon tone with stone textures and a clear way to
begin. The player enters a dungeon room where walls, crates, pressure plates,
locked doors, keys, enemies, and the exit staircase are visible on a grid.
Movement is turn-based: arrow keys move one tile, and all enemies move one
tile simultaneously.

Early rooms teach basic pushing: move a crate onto a plate to open a door.
Soon enemies appear that mirror the player's movement timing, forcing the
player to plan push sequences that also avoid or trap threats. Mid-game
introduces multiple crate types (heavy crates need two pushes, ice crates
slide until hitting a wall), keys that unlock color-coded doors, and items
found in chests. Late rooms combine all mechanics in procedurally arranged
layouts where the player must solve the spatial puzzle while managing enemy
positions.

An undo system lets the player rewind turns. Reaching the exit staircase
advances to the next floor. Death from enemy contact offers retry. The
campaign generates increasingly complex floors with more enemies, more crate
types, and tighter spatial constraints.

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
