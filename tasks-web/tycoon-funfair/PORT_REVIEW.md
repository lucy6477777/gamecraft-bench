# Rubric port review — tycoon-funfair

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if the screen mixes incompatible styles, relies on unthemed placeholder rectangles for primary elements, or reads as plain default Godot grey.
  **after**  Score 0 if the screen mixes incompatible styles, relies on unthemed placeholder rectangles for primary elements, or reads as a plain unstyled canvas with no background art.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Ride and stall art: rides and service stalls are real sprite art (illustrated, pixel-art, or hand-drawn fairground attractions), not solid-color rectangles or default Godot primitives, and different ride/amenity types are visually distinct and recognisable.
  **after**  Ride and stall art: rides and service stalls are real sprite art (illustrated, pixel-art, or hand-drawn fairground attractions), not solid-color rectangles or default raw drawn primitives, and different ride/amenity types are visually distinct and recognisable.

- **before** Score 0 if attractions are plain ColorRect / default shapes or indistinguishable blobs.
  **after**  Score 0 if attractions are plain solid-color rectangle / default shapes or indistinguishable blobs.

- **before** Score 0 if grounds are uniform color fills, if paths are plain ColorRect, or if guests are featureless dots/squares.
  **after**  Score 0 if grounds are uniform color fills, if paths are plain solid-color rectangle, or if guests are featureless dots/squares.

- **before** HUD and UI chrome: cash readout, guest count, satisfaction meter, build menu, price controls, and notice panels use styled themed widgets — custom panels, icon buttons, illustrated frames, or themed StyleBox — not raw unstyled Godot defaults, and numeric text uses a custom or styled font.
  **after**  HUD and UI chrome: cash readout, guest count, satisfaction meter, build menu, price controls, and notice panels use styled themed widgets — custom panels, icon buttons, illustrated frames, or themed CSS styling — not raw unstyled engine defaults, and numeric text uses a custom or styled font.

- **before** Score 0 if primary UI elements are obviously unstyled default Godot widgets or if chrome treatments differ wildly between screens.
  **after**  Score 0 if primary UI elements are obviously unstyled default unstyled DOM controls or if chrome treatments differ wildly between screens.
