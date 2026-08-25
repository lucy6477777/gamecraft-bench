# Rubric port review — platformer-vessel-of-hallownest

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if visible gameplay relies on ColorRect primitives, default Godot UI, or bright off-brief placeholder colors.
  **after**  Score 0 if visible gameplay relies on solid-color rectangle primitives, default unstyled default UI, or bright off-brief placeholder colors.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** UI chrome and atmospheric polish: title logo, map nodes, mask icons, soul meter, geo counter, boss HP, result panels, room transitions, particles, glow, and fog use themed frames, icons, or illustrated elements rather than naked Godot widgets.
  **after**  UI chrome and atmospheric polish: title logo, map nodes, mask icons, soul meter, geo counter, boss HP, result panels, room transitions, particles, glow, and fog use themed frames, icons, or illustrated elements rather than naked unstyled DOM controls.
