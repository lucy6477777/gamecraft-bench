# Rubric port review — platformer-cozy-harbor-delivery

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** The harbor environment uses real sprite or tile art for water, docks, islands, and buoys — not plain ColorRect fills or default Godot primitives.
  **after**  The harbor environment uses real sprite or tile art for water, docks, islands, and buoys — not plain solid-color rectangle fills or default raw drawn primitives.

- **before** HUD and UI chrome: cargo indicators, order panels, timer displays, upgrade menus, and result screens use styled themed widgets (custom panels, icon buttons, illustrated frames, or themed StyleBox), not raw unstyled Godot defaults.
  **after**  HUD and UI chrome: cargo indicators, order panels, timer displays, upgrade menus, and result screens use styled themed widgets (custom panels, icon buttons, illustrated frames, or themed CSS styling), not raw unstyled engine defaults.

- **before** Score 0 if primary UI elements are obviously unstyled default Godot widgets or if chrome treatments differ wildly between screens.
  **after**  Score 0 if primary UI elements are obviously unstyled default unstyled DOM controls or if chrome treatments differ wildly between screens.
