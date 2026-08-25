# Rubric port review — tycoon-wildhaven

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if the screen mixes incompatible styles, relies on unthemed placeholder rectangles, or reads as plain default Godot grey.
  **after**  Score 0 if the screen mixes incompatible styles, relies on unthemed placeholder rectangles, or reads as a plain unstyled canvas with no background art.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Score 0 if the map is uniform color fills, if terrain is plain ColorRect, or if seasonal change is only a text label.
  **after**  Score 0 if the map is uniform color fills, if terrain is plain solid-color rectangle, or if seasonal change is only a text label.

- **before** Buildings, workers, tools, and animals are real sprite art (illustrated, pixel-art, or hand-drawn), not solid-color rectangles or default Godot primitives.
  **after**  Buildings, workers, tools, and animals are real sprite art (illustrated, pixel-art, or hand-drawn), not solid-color rectangles or default raw drawn primitives.

- **before** Score 0 if buildings or animals are plain ColorRect or default shapes, or if upgraded production has no visual presence.
  **after**  Score 0 if buildings or animals are plain solid-color rectangle or default shapes, or if upgraded production has no visual presence.

- **before** HUD and UI chrome: cash readout, season indicator, industry panels, build menus, and event notices use styled themed widgets (custom panels, icon buttons, illustrated frames, themed StyleBox) with a custom or styled font.
  **after**  HUD and UI chrome: cash readout, season indicator, industry panels, build menus, and event notices use styled themed widgets (custom panels, icon buttons, illustrated frames, themed CSS styling) with a custom or styled font.

- **before** Score 0 if primary UI elements are obviously unstyled default Godot widgets or if the interface feels like debug controls.
  **after**  Score 0 if primary UI elements are obviously unstyled default unstyled DOM controls or if the interface feels like debug controls.
