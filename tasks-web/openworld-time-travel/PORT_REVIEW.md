# Rubric port review — openworld-time-travel

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** A title screen is present and styled: it shows the game name in a custom or themed font, has at minimum a 'Begin Journey' or 'Play' button that is interactive (clicking it transitions to the game world), and uses a non-default background (overlapping era landscapes, clock imagery, or temporal aurora) -- not plain Godot grey or a solid-colour fill.
  **after**  A title screen is present and styled: it shows the game name in a custom or themed font, has at minimum a 'Begin Journey' or 'Play' button that is interactive (clicking it transitions to the game world), and uses a non-default background (overlapping era landscapes, clock imagery, or temporal aurora) -- not a plain unstyled canvas with no background art or a solid-colour fill.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Score 0 if the screen mixes incompatible styles, or if elements are obviously unthemed placeholder shapes (solid-colour rectangles, default Godot primitives).
  **after**  Score 0 if the screen mixes incompatible styles, or if elements are obviously unthemed placeholder shapes (solid-colour rectangles, default raw drawn primitives).

- **before** Environment, character, and UI art quality: each era uses textured or illustrated tiles with visible surface detail that reads clearly at 1280x720; the player character and NPCs are recognisable sprites (not plain coloured rectangles); the time-travel device has a distinct sprite; HUD and inventory panels use styled, themed widgets -- not raw unstyled Godot defaults.
  **after**  Environment, character, and UI art quality: each era uses textured or illustrated tiles with visible surface detail that reads clearly at 1280x720; the player character and NPCs are recognisable sprites (not plain coloured rectangles); the time-travel device has a distinct sprite; HUD and inventory panels use styled, themed widgets -- not raw unstyled engine defaults.
