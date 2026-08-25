# Rubric port review — cardgame-poker-roguelike

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** A title screen is present and styled: it shows the game name in a custom or themed font, has at minimum a play button that is interactive and transitions to the game, and uses a non-default background (casino felt, card artwork, or noir aesthetic) — not plain Godot grey or a solid-colour fill.
  **after**  A title screen is present and styled: it shows the game name in a custom or themed font, has at minimum a play button that is interactive and transitions to the game, and uses a non-default background (casino felt, card artwork, or noir aesthetic) — not a plain unstyled canvas with no background art or a solid-colour fill.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
