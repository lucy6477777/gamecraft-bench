# Rubric port review — strategy-ashen-spire

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if the game launches directly into combat/map or the title is plain default Godot UI.
  **after**  Score 0 if the game launches directly into combat/map or the title is plain default unstyled default UI.

- **before** Score 0 if the screen is dominated by unthemed primitives or default Godot grey.
  **after**  Score 0 if the screen is dominated by unthemed primitives or an unstyled canvas with no background art.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
