# Rubric port review — openworld-racing

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** A title screen is present and styled: it shows the game name in a custom or themed font, has at minimum a play button that is interactive and transitions to the game world, and uses a non-default background (speed lines, sunset highway, or car silhouette) — not plain Godot grey or a solid-colour fill.
  **after**  A title screen is present and styled: it shows the game name in a custom or themed font, has at minimum a play button that is interactive and transitions to the game world, and uses a non-default background (speed lines, sunset highway, or car silhouette) — not a plain unstyled canvas with no background art or a solid-colour fill.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Environment, vehicle, and UI art quality: the world uses textured or illustrated tiles with visible surface detail that reads clearly at 1280x720; the vehicle is a distinct recognisable sprite (not a plain coloured rectangle); track barriers, checkpoints, and start lines use real game art; HUD panels, speedometers, and timers use styled, themed widgets — not raw unstyled Godot defaults.
  **after**  Environment, vehicle, and UI art quality: the world uses textured or illustrated tiles with visible surface detail that reads clearly at 1280x720; the vehicle is a distinct recognisable sprite (not a plain coloured rectangle); track barriers, checkpoints, and start lines use real game art; HUD panels, speedometers, and timers use styled, themed widgets — not raw unstyled engine defaults.
