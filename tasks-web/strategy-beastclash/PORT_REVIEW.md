# Rubric port review — strategy-beastclash

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if the screen mixes incompatible styles, relies on unthemed placeholder rectangles for primary elements, or reads as plain default Godot grey.
  **after**  Score 0 if the screen mixes incompatible styles, relies on unthemed placeholder rectangles for primary elements, or reads as a plain unstyled canvas with no background art.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Creature sprite quality: player and enemy creatures are represented by real sprite art (illustrated, pixel-art, or hand-drawn animals/monsters), not solid-color rectangles or default Godot primitives, and different creature types and tiers are visually distinct.
  **after**  Creature sprite quality: player and enemy creatures are represented by real sprite art (illustrated, pixel-art, or hand-drawn animals/monsters), not solid-color rectangles or default raw drawn primitives, and different creature types and tiers are visually distinct.

- **before** Score 0 if any in-battle creature is a plain ColorRect or default shape, or if creatures are indistinguishable colored blobs.
  **after**  Score 0 if any in-battle creature is a plain solid-color rectangle or default shape, or if creatures are indistinguishable colored blobs.

- **before** Score 0 if the battlefield is a uniform color background, if the terrain is plain ColorRect, or if the dens are solid-color blocks with no surface treatment.
  **after**  Score 0 if the battlefield is a uniform color background, if the terrain is plain solid-color rectangle, or if the dens are solid-color blocks with no surface treatment.

- **before** HUD chrome and UI styling: the food counter, evolution meter, den-health displays, creature spawn buttons, and result screens use styled themed widgets (custom panel backgrounds, icon buttons, illustrated frames, or themed StyleBox), not raw unstyled Godot defaults, and numeric counters use a custom or styled font.
  **after**  HUD chrome and UI styling: the food counter, evolution meter, den-health displays, creature spawn buttons, and result screens use styled themed widgets (custom panel backgrounds, icon buttons, illustrated frames, or themed CSS styling), not raw unstyled engine defaults, and numeric counters use a custom or styled font.

- **before** Score 0 if any primary HUD element is an obviously unstyled default Godot widget, or if chrome treatments differ wildly between screens.
  **after**  Score 0 if any primary HUD element is an obviously unstyled default unstyled DOM control, or if chrome treatments differ wildly between screens.
