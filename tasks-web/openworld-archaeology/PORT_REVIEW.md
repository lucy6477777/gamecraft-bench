# Rubric port review — openworld-archaeology

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default Godot widgets.
  **after**  Score 0.5 at most if the mechanic works but is represented entirely by programmatic shapes, solid-color fills, or default unstyled DOM controls.

- **before** Each biome reads as a coherent themed environment rather than mismatched parts or default Godot grey.
  **after**  Each biome reads as a coherent themed environment rather than mismatched parts or an unstyled canvas with no background art.

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, solid fills, or untextured geometry) instead of real illustrated or pixel-art assets.

- **before** Character and object sprite quality: the player avatar, artefacts, tools, and puzzle elements are real sprite art (illustrated, pixel-art, or hand-drawn), not solid-color rectangles or default Godot primitives.
  **after**  Character and object sprite quality: the player avatar, artefacts, tools, and puzzle elements are real sprite art (illustrated, pixel-art, or hand-drawn), not solid-color rectangles or default raw drawn primitives.

- **before** Score 0 if the avatar or artefacts are plain ColorRect/default shapes or indistinguishable colored blobs.
  **after**  Score 0 if the avatar or artefacts are plain solid-color rectangle/default shapes or indistinguishable colored blobs.

- **before** HUD and UI use styled themed widgets, not raw unstyled Godot defaults.
  **after**  HUD and UI use styled themed widgets, not raw unstyled engine defaults.
