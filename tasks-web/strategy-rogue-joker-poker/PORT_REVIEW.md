# Rubric port review — strategy-rogue-joker-poker

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if the game launches directly into a round, or if the title is plain default Godot UI.
  **after**  Score 0 if the game launches directly into a round, or if the title is plain default unstyled default UI.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Table, shop, and HUD chrome use themed styling: custom panel backgrounds, icon buttons, illustrated frames, chip/coin motifs, or themed Godot StyleBox rather than raw unstyled defaults.
  **after**  Table, shop, and HUD chrome use themed styling: custom panel backgrounds, icon buttons, illustrated frames, chip/coin motifs, or themed CSS styling rather than raw unstyled defaults.

- **before** Score 0 if primary HUD elements are obviously unstyled default Godot widgets.
  **after**  Score 0 if primary HUD elements are obviously unstyled default unstyled DOM controls.
