# Grim Fable

Build **Grim Fable**, a branching dark-fairytale visual novel, as a Web game (HTML5 canvas / Phaser) in the current working directory. This is not a prototype. It is a **complete, shippable
micro-game** that could sit on an itch.io page or Steam as a polished vertical
slice.

## Core Vision

You step into fairy tales you think you already know — but the woods are darker
than you remember, the kind are not always good, and the wicked may have their
reasons. Grim Fable is a **choice-driven visual novel** where the player relives
familiar storybook tales as their protagonist, yet the choices on offer were
never in the original telling. What looks like a bedtime story hides an uneasy
truth, and the player's decisions decide which version of that truth comes to
pass.

The fantasy is **rewriting a story you assume you know**. The game should turn
the player's own expectations into the trap: a beloved tale opens the familiar
way, then forks toward outcomes the fairy tale never allowed. The heart of the
loop is **read, examine, weigh, decide** — taking in a richly written scene,
looking closely at what the illustration is hiding, sizing up who and what to
trust, and committing to a choice that the story remembers and pays off later.
It should feel like turning the pages of a haunted picture book where text,
portraits, backdrops, and choice menus all belong to the same authored world.
This is a polished, atmospheric storybook with real stakes and genuinely
different endings, not a linear text dump with a single path.

## What the Player Experiences

1. **An Authored Opening** — From a styled title the player begins the tale and
   is eased into a familiar fairy-tale premise, presented as an illustrated
   storybook scene with characters, narration, and a clear sense of who they
   are and where they stand.
2. **Reading & Examining the Scene** — The story unfolds through paced dialogue
   and narration over illustrated backdrops, but the scene is not just read — it
   invites investigation. Props, details of the setting, and the characters
   present can hide narration, clues, or secrets the player would otherwise
   miss, so the comforting tale's darker underside is something the player
   uncovers, not just something told to them.
3. **Clues That Add Up** — What the player examines and learns is **gathered and
   remembered**: a blood-flecked knife noticed on a table, a confession teased
   out of a character, a detail that contradicts the storybook version. These
   discoveries accumulate into the player's understanding and unlock or color
   the choices and revelations that follow, rewarding a curious player who looks
   closely over one who rushes ahead.
4. **Meaningful Choices** — At key moments the player is offered choices that
   the original story never gave them — whom to trust, what to reveal, which
   path to take through the wood. Choices are deliberate decisions with stakes,
   not cosmetic flavor; what the player has uncovered shapes which options are
   available and what they mean, and the game makes clear that a decision has
   been made and registered.
5. **Consequences That Stick** — Earlier choices are remembered and shape what
   comes later: which characters confide in the player, what truths surface,
   and which doors close. The player should feel the story bending around their
   decisions rather than running on rails, and recurring tales or returning
   characters should reflect what the player did before.
6. **Divergent Endings** — The tale resolves in one of several genuinely
   different endings — a subversion of the happy ending, a grim reckoning, a
   hidden truth uncovered, or a quiet escape — each reachable through different
   choices and clearly tied to how the player played. The ending is an authored,
   styled conclusion that names what the player's path brought about, and the
   player can begin again to seek a different one.

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
