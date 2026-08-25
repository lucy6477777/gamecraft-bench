# Rubric port review — strategy-skirmish

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Score 0 if visible gameplay relies on raw ColorRect shapes, default Godot widgets, mismatched asset packs, or bright off-brief placeholder colors.
  **after**  Score 0 if visible gameplay relies on raw solid-color rectangle shapes, default unstyled DOM controls, mismatched asset packs, or bright off-brief placeholder colors.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Score 0 if the UI is mostly default Godot controls or plain floating text.
  **after**  Score 0 if the UI is mostly default unstyled DOM controls or plain floating text.
