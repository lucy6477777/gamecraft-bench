# Rubric port review — openworld-pokemon

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Score 0.5 at most if regions exist but use only programmatic shapes or uniform ColorRect fills instead of textured/illustrated tiles.
  **after**  Score 0.5 at most if regions exist but use only programmatic shapes or uniform solid-color rectangle fills instead of textured/illustrated tiles.

- **before** Score 0.5 at most if the information is present but uses raw unstyled Godot Label/Button defaults with no visual hierarchy or grouping.
  **after**  Score 0.5 at most if the information is present but uses raw unstyled unstyled text/Button defaults with no visual hierarchy or grouping.

- **before** A title screen is present and styled: it shows the game name in a custom or themed font, has at minimum a 'Start Adventure' or 'Play' button that is interactive (clicking it transitions to the game world), and uses a non-default background (landscape artwork, sky scene, or illustrated world map) — not plain Godot grey or a solid-colour fill.
  **after**  A title screen is present and styled: it shows the game name in a custom or themed font, has at minimum a 'Start Adventure' or 'Play' button that is interactive (clicking it transitions to the game world), and uses a non-default background (landscape artwork, sky scene, or illustrated world map) — not a plain unstyled canvas with no background art or a solid-colour fill.

- **before** Score 0.5 at most if the title screen exists but uses only solid-colour rectangles or default Godot widgets with no authored visual design.
  **after**  Score 0.5 at most if the title screen exists but uses only solid-colour rectangles or default unstyled DOM controls with no authored visual design.

- **before** Score 0 if the screen mixes incompatible styles, or if creatures and terrain are obviously unthemed placeholder shapes (solid-colour rectangles, default Godot primitives).
  **after**  Score 0 if the screen mixes incompatible styles, or if creatures and terrain are obviously unthemed placeholder shapes (solid-colour rectangles, default raw drawn primitives).

- **before** Score 0.5 at most if the game uses programmatic shapes (ColorRect, Polygon2D, StyleBoxFlat, solid-color fills) as primary visual elements instead of real illustrated or pixel-art assets.
  **after**  Score 0.5 at most if the game uses programmatic shapes (solid-color rectangles, Polygon2D, CSS stylingFlat, solid-color fills) as primary visual elements instead of real illustrated or pixel-art assets.

- **before** Environment, character, and UI art quality: the world map uses textured or illustrated tiles with visible surface detail that reads clearly at 1280x720; characters, creatures, and NPCs are distinct recognisable sprites (not plain coloured rectangles); HUD panels, skill buttons, dialog boxes, and capture-ball button use styled, themed widgets — custom panel backgrounds, icon buttons, illustrated frames, or rounded buttons — not raw unstyled Godot Label/Button/ColorRect defaults.
  **after**  Environment, character, and UI art quality: the world map uses textured or illustrated tiles with visible surface detail that reads clearly at 1280x720; characters, creatures, and NPCs are distinct recognisable sprites (not plain coloured rectangles); HUD panels, skill buttons, dialog boxes, and capture-ball button use styled, themed widgets — custom panel backgrounds, icon buttons, illustrated frames, or rounded buttons — not raw unstyled unstyled text/Button/solid-color rectangle defaults.

- **before** Score 0 if the map is a uniform colour fill, if units are solid-colour primitives, or if any primary HUD or dialog element is an obviously unstyled default Godot widget.
  **after**  Score 0 if the map is a uniform colour fill, if units are solid-colour primitives, or if any primary HUD or dialog element is an obviously unstyled default unstyled DOM control.
