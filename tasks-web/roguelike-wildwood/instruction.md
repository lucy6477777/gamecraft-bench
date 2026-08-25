# Roguelike: Wildwood

Build a **node-map forest-exploration roguelike with turn-based combat** as a Web game (HTML5 canvas / Phaser) in the current working directory. This is not a prototype. It is a **complete,
shippable micro-game** that could sit on an itch.io page or Steam as a polished
vertical slice.

## Core Vision

The fantasy is reading a dangerous forest. Every fork in the trail is a bet
placed with incomplete information: claw marks on a trunk, smoke curling above
the canopy, a glint of metal in the undergrowth. The player pushes deeper not
because the path is safe but because the clues make the risk feel knowable. When
a beast appears, combat is deliberate and positional — a small kit of skills
spent against creatures that each punish a different mistake. Health never
refills for free, so every scratch from three clearings ago still matters at the
final gate. Death is permanent for the run, but not for the player: banked gold
and a dwindling supply of entry tickets give each expedition weight without
making failure a dead end. The tone is hushed and watchful — dappled light,
distant howls, the crackle of a campfire earned by surviving one more node.

## What the Player Experiences

The player begins at a trailhead camp that remembers them between sessions —
tickets, gold, and whatever lasting advantages they have earned are all visible
here. Entering the forest costs a ticket, so the decision to set out already
carries stakes.

Once inside, the run unfolds as a branching map of trail nodes stretching deeper
into the wood. Nodes are not fully revealed; instead the map offers partial
evidence — tracks, smoke, glitter, disturbed brush — that lets the player weigh
risk against their current health, gold, and depth. Committing to a node strips
away the mystery: it might be a beast, a chest, a campfire, a trader, a trap, or
something worse.

Combat is turn-based and skill-driven. The hero carries several distinct
abilities that cost a resource, and different beasts demand different responses —
a fast wolf, an armored bear, a venomous serpent. Lingering conditions like
poison or bleed play out over multiple turns, rewarding the player who reads the
threat and plans ahead.

Between fights the player collects relics and gear that reshape how the hero
fights, not just refill health. Growth within a run is tangible: new buttons, new
options, new ways to handle what the forest throws next.

A run ends in victory — reaching the heart of the wood and overcoming its
guardian — or in death, which sends the player back to camp minus a ticket but
richer in banked gold. Progress persists across sessions, so quitting and
returning picks up the same hoard and the same slow accumulation of power.

## Assets

Produce the game's art through the asset workflow you were given. Generated
sprites, tiles, UI and audio belong under `public/assets/`, loaded by the
game at runtime.

Art quality is scored from what is actually on screen. A build whose visible
elements are drawn in code — solid-color rectangles, untextured geometry,
unstyled default controls — is capped well below full credit no matter how
correct the mechanics are.

## Project layout

Work in the current directory. It is your game's root — do not nest the project
inside another folder. The template you copy in already establishes the layout:

```
./
  index.html
  package.json          dev / build / typecheck scripts
  vite.config.js
  src/                  main.ts, LevelManager.ts, gameConfig.json, scenes/, chrome/
  public/assets/        images and audio the game loads at runtime
  dist/                 your production build — this is what gets evaluated
  demo_outputs/         ← your input traces (1–10 files)
```

Follow the template and asset workflow you were given; this section only adds
what the evaluator needs on top of it. Two things are required beyond a normal
build:

- a production build in `dist/`, and
- one or more replayable traces in `demo_outputs/`.

The build must complete and the built page must come up cleanly:

```
npm run build
```

The evaluator then serves `dist/` over a local static server and opens it in a
headless browser. It passes when three things hold: the page reaches the `load`
event, a `<canvas>` element is present, and no uncaught JavaScript error is
raised during startup. Serving matters — opening `dist/index.html` over `file://`
fails on module and asset loading and is not how the evaluator runs it.

Keep the first paint fast. Assets are decoded on the CPU here with no GPU, so a
handful of very large images can push the page past the load timeout; a build
that takes longer than 30 s to first paint is treated as a failed build.

## Demos

Ship **1–10 input-trace files** under `demo_outputs/`, one per demo, each named
`*.json`. The evaluator serves a fresh copy of your build per trace, replays
your trace as synthetic mouse and keyboard input at 1280×720, and records the
screen. Only the first 10 traces by filename are evaluated; recordings longer
than 20 s are sampled from a random 20 s window.

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
