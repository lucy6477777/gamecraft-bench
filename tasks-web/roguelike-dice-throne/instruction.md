# Dice Throne

Build **Dice Throne**, a dice-rolling roguelike with reroll mechanics and
equipment that modifies die faces as a Web game (HTML5 canvas / Phaser) in the current working directory. This is not
a prototype. It is a **complete, shippable micro-game** that could sit on an
itch.io page or Steam as a polished vertical slice.

## Core Vision

A warrior battles through a dungeon using dice as their combat system. Each
turn the player rolls a set of dice, then chooses which to keep and which to
reroll (up to two rerolls). Die faces map to abilities: swords deal damage,
shields block, hearts heal, and skulls trigger special attacks. The twist:
equipment found in the dungeon physically modifies die faces — a flame sword
replaces one sword face with a fire-sword that deals double damage, enchanted
armor adds a shield face to a die. The enemy rolls visible dice too, creating
a transparent contest where both sides see what is coming. Building a set of
dice with synergistic faces is the meta-progression within each run.

## What the Player Experiences

A title screen shows dice tumbling with glowing face icons. Starting a run
gives the player 5 standard dice (each with sword, sword, shield, heart,
skull, blank faces).

In combat, the player rolls all dice simultaneously with a satisfying tumble
animation. Results land face-up. The player selects dice to keep (they lock in
place) and rerolls the rest — up to two rerolls per turn. After finalizing,
faces activate: swords deal damage to the enemy, shields reduce incoming damage,
hearts heal, skulls trigger a special ability. The enemy then rolls their own
visible dice and resolves similarly.

Between encounters, loot screens offer equipment that modifies die faces —
replacing, upgrading, or adding faces. A map shows branching paths with combat,
elite, shop, and rest nodes. Shops sell face modifications and new dice. The
run ends at a boss with powerful custom dice. Death shows floor reached, best
roll, and equipment collected.

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
