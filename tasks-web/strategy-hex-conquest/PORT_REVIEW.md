# Rubric port review — strategy-hex-conquest

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** 0 if the screen mixes incompatible styles or reads as plain default Godot grey.
  **after**  0 if the screen mixes incompatible styles or reads as a plain unstyled canvas with no background art.

- **before** 0 if units are plain ColorRect or indistinguishable blobs.
  **after**  0 if units are plain solid-color rectangle or indistinguishable blobs.

- **before** The faction select, recruit menu, and result screens have authored chrome, not raw default Godot controls.
  **after**  The faction select, recruit menu, and result screens have authored chrome, not raw default unstyled DOM controls.
