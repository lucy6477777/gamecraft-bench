# Strategy: Tower-Defense

Build a **2D Tower-Defense Game** as a Web game (HTML5 canvas / Phaser) in the current working directory. This is not
a prototype. It is a **complete, shippable micro-game** that could sit on an
itch.io page or Steam as a polished vertical slice.

## Core Vision

The player is a field commander staring down a map of chokepoints and open
ground, watching a tide of hostiles pour along fixed corridors toward a
vulnerable endpoint. The only tool is a handful of deployable defenders and a
ticking resource clock. The fantasy is **spatial puzzle-solving under escalating
pressure** -- every tile placement is a commitment, every wave ratchets the
stakes, and the interesting tension is that resources spent now on a safe pick
could have been saved for a desperate answer later. The pressure comes from
reading the next wave's composition, choosing where to invest scarce Deployment
Points, and deciding whether to shore up a crumbling lane or gamble on a
high-cost unit that might turn the whole map. The risk is always that one
misread wave or one greedy save leaves the line too thin and enemies pour
through before the next DP tick arrives.

## What the Player Experiences

1. **Title and Campaign Entry** -- A cold, industrial title screen sets the tone.
   The player starts fresh or loads a save, then enters a stage-select map
   showing available missions, each hinting at the enemy composition and
   difficulty ahead.

2. **Deployment Phase** -- Inside a stage the player sees a grid battlefield with
   clearly marked paths, deployable tiles, and a base endpoint. DP ticks upward
   over time. The player drags unit cards from a hand onto legal tiles; each
   placement costs DP and commits a defender to that position. Invalid spots or
   insufficient funds refuse cleanly.

3. **The Assault** -- Enemies surge along the fixed path in discrete waves. Each
   wave is stronger or stranger than the last -- faster scouts, armored brutes,
   flying threats that bypass blockers. Defenders auto-attack within range,
   blockers hold the line, and the player watches HP bars tick down on both
   sides. Deaths remove units from the field; leaks chip away at the base's
   life total.

4. **Escalation and Adaptation** -- Later waves demand answers the opening
   roster cannot provide alone. The player weighs upgrades, repositions
   priorities, and stretches DP across competing needs. The map becomes a living
   puzzle of overlapping ranges and shifting pressure points.

5. **Resolution** -- The final wave breaks against the defense and victory is
   declared, or the base's life hits zero and defeat is acknowledged. Clearing
   a stage marks progress and unlocks the next. The player can retry, return to
   stage select, or quit to title without relaunching.

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
