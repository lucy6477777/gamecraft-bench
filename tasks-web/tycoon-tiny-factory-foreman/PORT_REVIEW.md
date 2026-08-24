# Rubric port review — tycoon-tiny-factory-foreman

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Belts, machines, sorters, and material items use real sprite art or carefully composed procedural visuals that read as factory equipment, not plain rectangles or default Godot primitives.
  **after**  Belts, machines, sorters, and material items use real sprite art or carefully composed procedural visuals that read as factory equipment, not plain rectangles or default raw drawn primitives.

- **before** Score 0 if primary gameplay elements are unstyled ColorRects.
  **after**  Score 0 if primary gameplay elements are unstyled solid-color rectangles.

- **before** HUD and UI panels use styled themed widgets with icons, framed panels, or custom fonts rather than raw unstyled Godot defaults.
  **after**  HUD and UI panels use styled themed widgets with icons, framed panels, or custom fonts rather than raw unstyled engine defaults.
