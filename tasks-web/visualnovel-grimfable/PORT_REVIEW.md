# Rubric port review — visualnovel-grimfable

Every sentence the term rules rewrote, deduplicated. Read each pair and
confirm the Web wording is exactly as strict as the Godot wording — a
looser threshold here inflates every score on this task.

- **before** Strong submissions rely on real illustrated or pixel-art treatment; a scene built mainly from ColorRects, circles, silhouettes, and flat primitive shapes should be judged low even if the colors are coherent.
  **after**  Strong submissions rely on real illustrated or pixel-art treatment; a scene built mainly from solid-color rectangles, circles, silhouettes, and flat primitive shapes should be judged low even if the colors are coherent.

- **before** Score 0 if the screen is dominated by default Godot widgets, untextured rectangles, or placeholder text.
  **after**  Score 0 if the screen is dominated by default unstyled DOM controls, untextured rectangles, or placeholder text.

- **before** The dialogue box, name plates, choice menus, clue panels, title, and ending screens use styled, themed UI — illustrated frames, ornamented panels, custom or styled fonts, and consistent chrome — fitting the dark-fairytale theme, rather than raw default Godot Label/Button/Panel defaults or plain flat boxes.
  **after**  The dialogue box, name plates, choice menus, clue panels, title, and ending screens use styled, themed UI — illustrated frames, ornamented panels, custom or styled fonts, and consistent chrome — fitting the dark-fairytale theme, rather than raw unstyled text/Button/Panel defaults or plain flat boxes.
