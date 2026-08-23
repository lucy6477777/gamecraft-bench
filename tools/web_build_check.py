#!/usr/bin/env python3
"""Web build gate: does the built page actually come up?

The Godot suite gates on `godot --headless --path <dir> --quit-after 5` exiting
0. This is the Web counterpart and it is deliberately just as hard, because the
gate is multiplicative -- a loose gate here inflates every score on every task.

Three conditions, all required:
  1. the page reaches the `load` event within the timeout,
  2. a <canvas> element exists and has non-zero size,
  3. no uncaught JavaScript error is raised during startup.

A fourth signal is measured and always reported, but only fails the gate in
one unambiguous case. Startup is not the only place a game can be dead: a
generated roguelike passed all three conditions above -- clean load, canvas
present, zero JS errors even at a 12s settle -- and then threw
`Cannot read properties of undefined (reading '2')` the instant the player
clicked, leaving a pure black canvas. It scored 0.094, but the judge reached
that number by describing frozen loading screens, so an outright crash was
recorded as if it were poor game quality.

So the probe clicks once and watches. `interaction_error` and
`canvas_froze` are reported either way. The gate fails only when BOTH hold:
an uncaught error was raised AND the canvas stopped changing afterwards. One
alone is not enough -- a turn-based game legitimately renders a still frame
while it waits for input, and a game can log an error and keep playing. Set
GAMECRAFT_BENCH_WEB_GATE_INTERACTION=0 to report without ever failing.

Serving matters: `file://` breaks module and asset loading, so the page is
served over a local static server exactly as the evaluator serves it.

Prints 1 (pass) or 0 (fail) on the last line and exits 0 either way, so a
failing build is a score of zero rather than a crashed verifier.

    python3 tools/web_build_check.py --project /workspace/game
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextlib.contextmanager
def _serve(root: Path, port: int):
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 10
        while time.time() < deadline:
            with socket.socket() as s:
                s.settimeout(0.3)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.2)
        yield
    finally:
        proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)


async def _probe(url: str, timeout_s: float, settle_s: float) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415

    result = {"loaded": False, "canvas": False, "canvas_size": None,
              "errors": [], "load_seconds": None}
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--disable-gpu", "--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await ctx.new_page()
        page.on("pageerror", lambda e: result["errors"].append(str(e)[:200]))
        page.on("console", lambda m: result["errors"].append(f"console.error: {m.text[:180]}")
                if m.type == "error" else None)
        t0 = time.time()
        try:
            await page.goto(url, wait_until="load", timeout=timeout_s * 1000)
            result["loaded"] = True
            result["load_seconds"] = round(time.time() - t0, 2)
        except Exception as exc:  # noqa: BLE001
            result["errors"].append(f"navigation: {type(exc).__name__}: {str(exc)[:160]}")

        if result["loaded"]:
            # Let the engine boot and draw at least one frame before judging it.
            await page.wait_for_timeout(int(settle_s * 1000))
            info = await page.evaluate(
                """() => {
                    const c = document.querySelector('canvas');
                    if (!c) return null;
                    const r = c.getBoundingClientRect();
                    return {w: Math.round(r.width), h: Math.round(r.height)};
                }""")
            if info and info["w"] > 0 and info["h"] > 0:
                result["canvas"] = True
                result["canvas_size"] = [info["w"], info["h"]]

            if result["canvas"]:
                startup_errors = len(result["errors"])
                shot_a = await page.screenshot()
                await page.mouse.click(info["w"] // 2, info["h"] // 2)
                await page.wait_for_timeout(1500)
                shot_b = await page.screenshot()
                await page.wait_for_timeout(1200)
                shot_c = await page.screenshot()
                result["interaction_error"] = len(result["errors"]) > startup_errors
                # Frozen means nothing moved across two intervals after the
                # click -- not merely that the click changed nothing.
                result["canvas_froze"] = (shot_b == shot_c)
                result["canvas_changed_on_click"] = (shot_a != shot_b)
        await browser.close()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--dist", default="dist",
                    help="build output dir relative to --project")
    ap.add_argument("--timeout", type=float, default=30.0,
                    help="seconds allowed to reach the load event")
    ap.add_argument("--settle", type=float, default=3.0,
                    help="seconds to let the engine boot before inspecting")
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    dist = args.project / args.dist
    report: dict = {"project": str(args.project), "dist": str(dist)}

    if not (dist / "index.html").is_file():
        report["errors"] = [f"no {args.dist}/index.html — the project was not built"]
        report["pass"] = False
    else:
        port = _free_port()
        with _serve(dist, port):
            try:
                probe = asyncio.run(_probe(f"http://127.0.0.1:{port}/",
                                           args.timeout, args.settle))
            except Exception as exc:  # noqa: BLE001
                probe = {"loaded": False, "canvas": False,
                         "errors": [f"probe failed: {type(exc).__name__}: {exc}"]}
        report.update(probe)
        base_ok = bool(probe.get("loaded") and probe.get("canvas")
                       and not probe.get("errors"))
        # Dead-on-first-input: an uncaught error AND a canvas that then stops
        # updating. Requiring both keeps a still-but-alive game passing.
        dead = bool(probe.get("interaction_error") and probe.get("canvas_froze"))
        report["dead_on_interaction"] = dead
        gate_on = (os.environ.get("GAMECRAFT_BENCH_WEB_GATE_INTERACTION") or "1") != "0"
        report["pass"] = base_ok and not (dead and gate_on)

    for line in (f"  loaded        {report.get('loaded')}"
                 f"  ({report.get('load_seconds')}s)",
                 f"  canvas        {report.get('canvas')}"
                 f"  {report.get('canvas_size') or ''}",
                 f"  js errors     {len(report.get('errors') or [])}",
                 f"  on click      changed={report.get('canvas_changed_on_click')}"
                 f"  error={report.get('interaction_error')}"
                 f"  froze={report.get('canvas_froze')}",
                 f"  dead on input {report.get('dead_on_interaction')}"):
        print(line)
    for err in (report.get("errors") or [])[:5]:
        print(f"    ! {err}")

    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=1))
    print(1 if report["pass"] else 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
