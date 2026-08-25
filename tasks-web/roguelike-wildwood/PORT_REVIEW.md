# Rubric port review — roguelike-wildwood

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if the screen mixes incompatible styles, relies on unthemed placeholder rectangles for primary elements, or reads as plain default Godot grey.
  **after**  Score 0 if the screen mixes incompatible styles, relies on unthemed placeholder rectangles for primary elements, or reads as a plain unstyled canvas with no background art.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Character and beast sprite quality: the hero and the various beasts are real sprite art (illustrated, pixel-art, or hand-drawn), not solid-color rectangles or default Godot primitives, and different beast types and the hero are visually distinct and recognisable.
  **after**  Character and beast sprite quality: the hero and the various beasts are real sprite art (illustrated, pixel-art, or hand-drawn), not solid-color rectangles or default raw drawn primitives, and different beast types and the hero are visually distinct and recognisable.

- **before** Score 0 if the hero or any in-combat beast is a plain ColorRect or default shape, or if beasts are indistinguishable colored blobs.
  **after**  Score 0 if the hero or any in-combat beast is a plain solid-color rectangle or default shape, or if beasts are indistinguishable colored blobs.

- **before** Score 0 if the map and environment are uniform color fills, if node markers are plain ColorRect dots, or if the camp is an unstyled blank screen.
  **after**  Score 0 if the map and environment are uniform color fills, if node markers are plain solid-color rectangle dots, or if the camp is an unstyled blank screen.

- **before** HUD and UI chrome: health/resource bars, gold and ticket readouts, skill buttons with icons, status-effect icons, inventory display, and camp/result screens use styled themed widgets — custom panels, icon buttons, illustrated frames, or themed StyleBox — not raw unstyled Godot defaults, and numeric text uses a custom or styled font.
  **after**  HUD and UI chrome: health/resource bars, gold and ticket readouts, skill buttons with icons, status-effect icons, inventory display, and camp/result screens use styled themed widgets — custom panels, icon buttons, illustrated frames, or themed CSS styling — not raw unstyled engine defaults, and numeric text uses a custom or styled font.

- **before** Score 0 if primary UI elements are obviously unstyled default Godot widgets or if chrome treatments differ wildly between screens.
  **after**  Score 0 if primary UI elements are obviously unstyled default unstyled DOM controls or if chrome treatments differ wildly between screens.
