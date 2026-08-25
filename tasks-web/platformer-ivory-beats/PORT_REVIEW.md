# Rubric port review — platformer-ivory-beats

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if the game relies on raw ColorRect shapes with no styling, default Godot widgets, or a cluttered mismatched color scheme.
  **after**  Score 0 if the game relies on raw solid-color rectangle shapes with no styling, default unstyled DOM controls, or a cluttered mismatched color scheme.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Score 0 if the UI is mostly naked Godot controls or plain floating text.
  **after**  Score 0 if the UI is mostly naked unstyled DOM controls or plain floating text.
