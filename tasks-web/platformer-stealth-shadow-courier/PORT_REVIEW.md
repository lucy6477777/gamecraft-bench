# Rubric port review — platformer-stealth-shadow-courier

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if most visible elements are default shapes, raw ColorRects, or unthemed placeholders.
  **after**  Score 0 if most visible elements are default shapes, raw solid-color rectangles, or unthemed placeholders.

- **before** The stealth environment uses real sprite or tile art for walls, floors, doors, cover, and lighting -- not plain ColorRect fills or default Godot primitives.
  **after**  The stealth environment uses real sprite or tile art for walls, floors, doors, cover, and lighting -- not plain solid-color rectangle fills or default raw drawn primitives.

- **before** HUD and UI chrome: mission panels, alert indicators, key/document icons, result screens, and menu buttons use styled themed widgets rather than raw unstyled Godot defaults.
  **after**  HUD and UI chrome: mission panels, alert indicators, key/document icons, result screens, and menu buttons use styled themed widgets rather than raw unstyled engine defaults.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
