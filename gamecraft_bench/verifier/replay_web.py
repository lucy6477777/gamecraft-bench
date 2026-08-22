"""Replay a demo trace against a built Web game and record the screen.

Drop-in counterpart to ``replay.py``: same ``replay_trace`` signature, same
``ReplayResult``, same ``ReplayError``. Everything downstream -- frame sampling,
the judge, aggregation, the score formula -- is engine-agnostic and untouched,
so swapping this module in is all a Web target needs.

Where Godot is driven with Xvfb + xdotool + ffmpeg x11grab, this drives a
headless Chromium through Playwright and takes the video Playwright already
records, then transcodes it to mp4 so the same sampler can read it.

Two things earn their complexity here.

Coordinates. A trace is authored in the game's own 1280x720 space, but the
canvas is letterboxed and scaled to fit the browser viewport. Measured on one
build: canvas at x=75, scaled 0.703. Replaying game coordinates directly missed
every target -- the recording looked like a game nobody was playing. So the
canvas rect is read from the live page and every coordinate is mapped through
it.

Pacing. Events carry frame numbers at a stated fps. Wall-clock sleeps drift,
so each event is scheduled against a single start timestamp rather than by
accumulating deltas; late events fire immediately rather than pushing
everything after them further out.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .replay import ReplayError, ReplayResult  # reuse the shared contract

_KEYCODE_TO_BROWSER = {
    "ESCAPE": "Escape", "ENTER": "Enter", "SPACE": "Space", "TAB": "Tab",
    "BACKSPACE": "Backspace", "DELETE": "Delete", "SHIFT": "Shift",
    "CTRL": "Control", "ALT": "Alt", "UP": "ArrowUp", "DOWN": "ArrowDown",
    "LEFT": "ArrowLeft", "RIGHT": "ArrowRight",
}


def _browser_key(keycode: str) -> str:
    """Map a trace keycode onto what a browser dispatches."""
    k = str(keycode).strip()
    if k.upper() in _KEYCODE_TO_BROWSER:
        return _KEYCODE_TO_BROWSER[k.upper()]
    if len(k) == 1 and k.isalpha():
        return f"Key{k.upper()}"
    if len(k) == 1 and k.isdigit():
        return f"Digit{k}"
    return k


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
        else:
            raise ReplayError(f"static server did not come up on port {port}")
        yield
    finally:
        proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)


@dataclass
class _Mapping:
    """Game-viewport pixels -> browser-viewport pixels."""
    ox: float
    oy: float
    sx: float
    sy: float

    def __call__(self, x: float, y: float) -> tuple[float, float]:
        return self.ox + x * self.sx, self.oy + y * self.sy


async def _read_canvas_mapping(page, game_w: int, game_h: int) -> _Mapping:
    info = await page.evaluate(
        """() => {
            const c = document.querySelector('canvas');
            if (!c) return null;
            const r = c.getBoundingClientRect();
            return {x: r.x, y: r.y, w: r.width, h: r.height};
        }""")
    if not info or info["w"] <= 0 or info["h"] <= 0:
        # No canvas: fall back to identity so key-only traces still replay, and
        # let the judge see whatever the page does render.
        return _Mapping(0.0, 0.0, 1.0, 1.0)
    return _Mapping(info["x"], info["y"], info["w"] / game_w, info["h"] / game_h)


async def _run(url: str, trace: dict, out_dir: Path, *, viewport: tuple[int, int],
               record_size: tuple[int, int], fps: int,
               settle_seconds: float, max_replay_seconds: float,
               ready_timeout: float) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415

    events = sorted(trace.get("events") or [], key=lambda e: e.get("frame", 0))
    duration_frames = int(trace.get("duration_frames") or 0)
    if duration_frames <= 0:
        duration_frames = (max(e.get("frame", 0) for e in events) + fps) if events else fps
    duration_frames = min(duration_frames, int(max_replay_seconds * fps))

    vid_dir = out_dir / "_video"
    vid_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--disable-gpu", "--no-sandbox"])
        # Recording begins with the context, which is before navigation, asset
        # loading and settle. Downstream sampling draws its window from t=0 for
        # the *trace's* duration, so that lead-in both wastes frames on a
        # loading screen and truncates an equal slice off the end of actual
        # play. Remember where the trace really starts and cut it off below.
        t_recording_start = time.monotonic()
        ctx = await browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            record_video_dir=str(vid_dir),
            record_video_size={"width": record_size[0], "height": record_size[1]})
        page = await ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))

        try:
            await page.goto(url, wait_until="load", timeout=30_000)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"navigation: {type(exc).__name__}: {str(exc)[:160]}")
        # `load` fires before a Phaser game has its assets. These builds pull
        # a dozen generated images afterwards, and a fixed 1.5s settle put the
        # first keypresses on a "Loading..." progress bar: measured on the
        # sokoban demo, seven key presses produced no movement and the judge
        # correctly reported that no movement was demonstrated. Wait for the
        # asset requests to actually finish, then settle.
        try:
            await page.wait_for_load_state("networkidle", timeout=int(ready_timeout * 1000))
        except Exception:  # noqa: BLE001
            errors.append(f"assets still loading after {ready_timeout:.0f}s; "
                          f"replaying anyway")
        await page.wait_for_timeout(int(settle_seconds * 1000))

        mapping = await _read_canvas_mapping(page, viewport[0], viewport[1])

        start = time.monotonic()

        async def _at(frame: int) -> None:
            """Sleep until this frame's wall-clock slot; never rewind."""
            target = start + frame / float(fps)
            delay = target - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)

        for ev in events:
            await _at(int(ev.get("frame", 0)))
            etype = ev.get("type")
            try:
                if etype in ("mouse_click", "mouse_down", "mouse_up", "mouse_move"):
                    x, y = mapping(float(ev.get("x", 0)), float(ev.get("y", 0)))
                    button = ev.get("button", "left")
                    if etype == "mouse_click":
                        await page.mouse.click(x, y, button=button)
                    elif etype == "mouse_down":
                        await page.mouse.move(x, y)
                        await page.mouse.down(button=button)
                    elif etype == "mouse_up":
                        await page.mouse.move(x, y)
                        await page.mouse.up(button=button)
                    else:
                        await page.mouse.move(x, y)
                elif etype in ("key_press", "key_down", "key_up"):
                    key = _browser_key(ev.get("keycode", ""))
                    if etype == "key_press":
                        await page.keyboard.press(key)
                    elif etype == "key_down":
                        await page.keyboard.down(key)
                    else:
                        await page.keyboard.up(key)
                elif etype == "wait":
                    pass
                else:
                    errors.append(f"unknown event type {etype!r}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{etype} at frame {ev.get('frame')}: "
                              f"{type(exc).__name__}: {str(exc)[:120]}")

        await _at(duration_frames)
        video = page.video
        await ctx.close()          # finalises the video file
        webm = Path(await video.path()) if video else None
        await browser.close()

    return {"webm": webm, "duration_seconds": duration_frames / float(fps),
            "lead_in_seconds": max(0.0, start - t_recording_start),
            "errors": errors}


def _to_mp4(webm: Path, mp4: Path, *, skip_seconds: float = 0.0) -> None:
    mp4.parent.mkdir(parents=True, exist_ok=True)
    seek = ["-ss", f"{skip_seconds:.3f}"] if skip_seconds > 0.05 else []
    proc = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *seek, "-i", str(webm),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(mp4)],
        capture_output=True, text=True)
    if proc.returncode != 0 or not mp4.is_file():
        raise ReplayError(f"ffmpeg failed to transcode {webm.name}: "
                          f"{proc.stderr.strip()[:200]}")


def replay_trace(
    *,
    project_dir: Path,
    trace_path: Path,
    output_mp4: Path,
    viewport: tuple[int, int] = (1280, 720),
    record_size: tuple[int, int] | None = (854, 480),
    fps: int = 30,
    dist_subdir: str = "dist",
    settle_seconds: float = 1.5,
    ready_timeout: float = 20.0,
    log_dir: Path | None = None,
    max_replay_seconds: float = 90.0,
) -> ReplayResult:
    """Serve the built game, replay one trace against it, record an mp4."""
    dist = project_dir / dist_subdir
    if not (dist / "index.html").is_file():
        raise ReplayError(f"no {dist_subdir}/index.html under {project_dir} "
                          f"— the project was not built")
    try:
        trace = json.loads(Path(trace_path).read_text())
    except Exception as exc:  # noqa: BLE001
        raise ReplayError(f"unreadable trace {trace_path}: {exc}") from exc

    scenario = trace.get("scenario")
    out_dir = output_mp4.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    if scenario:
        url += f"?scenario={scenario}"

    with _serve(dist, port):
        try:
            res = asyncio.run(_run(
                url, trace, out_dir, viewport=viewport,
                record_size=tuple(record_size or viewport), fps=fps,
                settle_seconds=settle_seconds,
                max_replay_seconds=max_replay_seconds,
                ready_timeout=ready_timeout))
        except ReplayError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ReplayError(f"browser replay failed: "
                              f"{type(exc).__name__}: {exc}") from exc

    if not res["webm"] or not Path(res["webm"]).is_file():
        raise ReplayError("browser produced no recording")
    _to_mp4(Path(res["webm"]), output_mp4,
            skip_seconds=res.get("lead_in_seconds", 0.0))
    shutil.rmtree(out_dir / "_video", ignore_errors=True)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "replay_web.json").write_text(json.dumps(
            {"url": url, "scenario": scenario, "fps": fps,
             "duration_seconds": res["duration_seconds"],
             "lead_in_seconds": round(res.get("lead_in_seconds", 0.0), 2),
             "n_events": len(trace.get("events") or []),
             "errors": res["errors"]}, indent=1))

    return ReplayResult(output_mp4=output_mp4,
                        duration_seconds=res["duration_seconds"],
                        godot_returncode=0)
