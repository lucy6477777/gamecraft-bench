# Rubric port review — platformer-wall-dancer

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Room environments use real sprite or tile art for walls, platforms, backgrounds, and hazards — not plain ColorRect fills or default Godot primitives.
  **after**  Room environments use real sprite or tile art for walls, platforms, backgrounds, and hazards — not plain solid-color rectangle fills or default raw drawn primitives.

- **before** HUD and UI chrome: death counter, timer, chapter select, and results screens use styled themed widgets with custom panels, icon buttons, or themed StyleBox — not raw unstyled Godot defaults.
  **after**  HUD and UI chrome: death counter, timer, chapter select, and results screens use styled themed widgets with custom panels, icon buttons, or themed CSS styling — not raw unstyled engine defaults.

- **before** Score 0 if primary UI elements are obviously unstyled default Godot widgets.
  **after**  Score 0 if primary UI elements are obviously unstyled default unstyled DOM controls.
