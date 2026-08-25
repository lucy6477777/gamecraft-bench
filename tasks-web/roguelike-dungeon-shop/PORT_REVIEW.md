# Rubric port review — roguelike-dungeon-shop

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Items have distinct illustrated sprites, customers have character art, and the shop interior uses real tile/sprite assets — not plain ColorRect fills.
  **after**  Items have distinct illustrated sprites, customers have character art, and the shop interior uses real tile/sprite assets — not plain solid-color rectangle fills.

- **before** HUD and UI chrome: price sliders, gold display, customer panels, upgrade shop, and result screens use styled themed widgets — not raw unstyled Godot defaults.
  **after**  HUD and UI chrome: price sliders, gold display, customer panels, upgrade shop, and result screens use styled themed widgets — not raw unstyled engine defaults.
