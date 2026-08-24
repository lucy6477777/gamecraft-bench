# Rubric port review — platformer-knight-quest

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Stage environments use real sprite or tile art for platforms, backgrounds, enemies, and the knight — not plain ColorRect fills.
  **after**  Stage environments use real sprite or tile art for platforms, backgrounds, enemies, and the knight — not plain solid-color rectangle fills.

- **before** HUD and UI chrome: health bar, gem counter, sub-weapon panel, shop interface, and boss health bar use styled themed widgets — not raw unstyled Godot defaults.
  **after**  HUD and UI chrome: health bar, gem counter, sub-weapon panel, shop interface, and boss health bar use styled themed widgets — not raw unstyled engine defaults.
