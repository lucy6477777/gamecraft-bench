"""OpenAI / GPT judge backend (frame-sampling chat completions).

Sends the demo's pre-sampled PNG frames (one image per
``--frame-interval-seconds`` of replay) to a GPT model via the
chat-completions API, and parses a strict-JSON reply containing one
score per requirement.

Why frames and not video: the hosted endpoints we currently use
(third-party proxies + the public OpenAI API on chat-completions)
either reject ``input_video`` outright or silently decode only the
first frame of an animated container. Sending discrete frames is the
shape every vendor accepts today.

Honours ``OPENAI_API_KEY`` and the optional ``OPENAI_BASE_URL`` for
proxy routing. The backend also forwards any extra HTTP headers found
in ``OPENAI_EXTRA_HEADERS_JSON`` (a JSON object), which is how proxies
that gate on user-agent (e.g. tokenrun) get unblocked.
"""

from __future__ import annotations

import base64
import functools
import io
import json
import os
from pathlib import Path

from . import _common
from .base import JudgeError, JudgeRequest, JudgeResponse, MultimodalJudge

# Upper bound on frames sent in one chat-completions request. The official
# default is 40. Some OpenAI-compatible proxies cap the HTTP body well below
# what 40 full-size PNG frames encode to (measured on one internal router:
# 36 frames / ~4.18 MB -> 200, 38 frames / ~4.46 MB -> 413 body_too_large),
# and a 413 makes the whole demo score 0 rather than degrading gracefully.
# Override with GAMECRAFT_BENCH_JUDGE_MAX_FRAMES; the default is unchanged.
_MAX_FRAMES = max(1, int(os.environ.get("GAMECRAFT_BENCH_JUDGE_MAX_FRAMES") or 40))
# Reasoning models spend this budget before emitting any visible content, so a
# budget that merely fits the answer returns an empty string instead, and an
# empty response is a failed call.
#
# Measured on gpt-5.5, 24 calls over two rubrics with real frames, given an
# unreachable ceiling so the numbers are demand rather than truncation:
#
#     total completion tokens   min 1149   median ~1900   max 2974
#     the official 2048 budget truncates 7 of 18 resampled calls (38%)
#
# Demand does NOT scale with rubric size -- a 14-requirement rubric had the
# heavier median (2211) than a 20-requirement one (1630), and the spread within
# a single rubric (1595-2974) exceeds the spread between rubrics. So 2048 is
# not "too small for hard tasks", it sits inside the ordinary run-to-run
# distribution, which is why the failure looked random.
#
# 4096 covered every sample but only 1.38x the observed max, and the ceiling
# is not a charge -- unused budget costs nothing. 8192 buys 2.75x for free.
_MAX_TOKENS = max(256, int(os.environ.get("GAMECRAFT_BENCH_JUDGE_MAX_TOKENS") or 8192))
# Optional payload budget in MB for one judge request (0/unset = no budget,
# i.e. official behaviour). See _select_frames for why bytes beat frame count.
_MAX_BODY_BYTES = int(float(os.environ.get("GAMECRAFT_BENCH_JUDGE_MAX_BODY_MB") or 0) * 1_000_000)


def _parse_sse_to_text(raw: str) -> str:
    """Reassemble content from a force-streamed SSE response string."""
    import json as _json
    parts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            chunk = _json.loads(payload)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            parts.append(delta.get("content") or "")
        except Exception:
            continue
    return "".join(parts)


# Frames go out as JPEG by default. PNG size tracks art style rather than
# information: measured at an identical 854x480, a Phaser build with a painted
# background averaged 450 KB per frame against 225 KB for a Godot build, so the
# same byte budget bought 4 frames for one engine and 36 for the other -- and
# 4 frames of a 17-second recording is its title screen, which is exactly what
# the judge reported seeing. Re-encoded to JPEG q85 both average 55 KB, so the
# budget buys the same ~40 frames either way and the comparison stops depending
# on how the game is drawn. Set GAMECRAFT_BENCH_JUDGE_FRAME_FORMAT=png to send
# the original bytes.
_FRAME_FORMAT = (os.environ.get("GAMECRAFT_BENCH_JUDGE_FRAME_FORMAT") or "jpeg").strip().lower()
_FRAME_QUALITY = max(1, min(95, int(os.environ.get("GAMECRAFT_BENCH_JUDGE_FRAME_QUALITY") or 85)))


@functools.lru_cache(maxsize=512)
def _encoded_frame(path: Path) -> tuple[bytes, str]:
    """Bytes actually sent for one frame, plus its mime subtype."""
    raw = path.read_bytes()
    if _FRAME_FORMAT == "png":
        return raw, "png"
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        return raw, path.suffix.lstrip(".").lower() or "png"
    buf = io.BytesIO()
    with Image.open(path) as im:
        im.convert("RGB").save(buf, "JPEG", quality=_FRAME_QUALITY, optimize=True)
    return buf.getvalue(), "jpeg"


def _data_uri(path: Path) -> str:
    payload, kind = _encoded_frame(path)
    b64 = base64.standard_b64encode(payload).decode("ascii")
    return f"data:image/{kind};base64,{b64}"


def _evenly_spaced(frames: list[Path], n: int) -> list[Path]:
    """n frames spanning the whole list, always including first and last.

    The obvious `int(i * len/n)` is only approximately even, and it degenerates
    badly when n approaches len(frames): at n = len-1 the step is 1.03, int()
    truncates every index to i, and the result is the first n frames rather
    than a spread. Iterating that to shrink a payload took a 17-second
    recording down to its first four frames -- the title screen -- and the
    judge then correctly reported that it had been shown nothing but a title
    screen. Anchoring on len-1 / n-1 keeps the span exact at every n.
    """
    if n <= 0:
        return []
    if len(frames) <= n:
        return list(frames)
    if n == 1:
        return [frames[len(frames) // 2]]      # a middle frame beats frame 0
    last = len(frames) - 1
    return [frames[round(i * last / (n - 1))] for i in range(n)]


def _select_frames(frames: list[Path]) -> list[Path]:
    """Evenly-spaced subset, capped by count and (optionally) by payload size.

    The count cap alone is not safe on a proxy with an HTTP body limit,
    because frame *bytes* vary with how much art is on screen. Measured on
    one task: a shapes-only reference build averaged 61-88 KB per frame
    while an agent build using real sprite assets averaged 109-156 KB --
    so the same frame count is 3.4 MB for one and 6.0 MB for the other.
    Capping on count therefore fails exactly on the richer-looking build,
    which biases scoring against better art. Budget on bytes instead.
    """
    picked = _evenly_spaced(frames, _MAX_FRAMES)
    if _MAX_BODY_BYTES <= 0:
        return picked
    # base64 inflates by 4/3; leave the remainder for prompt + JSON overhead.
    def encoded(sel: list[Path]) -> int:
        # Measure the bytes that actually go on the wire. Using the on-disk
        # PNG size here would budget for a payload we are not sending.
        return int(sum(len(_encoded_frame(f)[0]) for f in sel) * 4 / 3)
    while len(picked) > 1 and encoded(picked) > _MAX_BODY_BYTES:
        picked = _evenly_spaced(picked, len(picked) - 1)
    return picked


def _extra_headers() -> dict[str, str]:
    raw = os.environ.get("OPENAI_EXTRA_HEADERS_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): str(v) for k, v in parsed.items()}


class OpenAIJudge(MultimodalJudge):
    name = "openai"
    default_model = "gpt-5.5"

    def score(self, request: JudgeRequest) -> JudgeResponse:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise JudgeError(f"openai SDK not installed: {e}") from e
        try:
            api_key = _common.require_env(
                "GAMECRAFT_BENCH_JUDGE_OPENAI_API_KEY", "OPENAI_API_KEY"
            )
        except KeyError as e:
            raise JudgeError(str(e)) from e

        if not request.frame_paths:
            raise JudgeError(
                f"no sampled frames available for demo {request.demo_id!r}"
            )

        client_kwargs: dict[str, object] = {"api_key": api_key}
        base_url = (
            _common.get_env("GAMECRAFT_BENCH_JUDGE_OPENAI_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
        )
        if base_url:
            client_kwargs["base_url"] = base_url
        extra = _extra_headers()
        if extra:
            client_kwargs["default_headers"] = extra
        client = OpenAI(**client_kwargs)

        frames = _select_frames(request.frame_paths)
        content: list[dict] = [
            {"type": "text",
             "text": (
                 f"The next {len(frames)} images are PNG frames sampled in "
                 "temporal order from one playthrough of a Godot 2D game."
             )},
        ]
        for idx, fp in enumerate(frames, start=1):
            content.append({
                "type": "image_url",
                "image_url": {"url": _data_uri(fp)},
            })
            content.append({"type": "text", "text": f"(frame {idx}/{len(frames)})"})
        content.append({
            "type": "text",
            "text": _common.build_user_prompt(request.requirements),
        })

        try:
            resp = client.chat.completions.create(
                model=self.model,
                max_tokens=_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": _common.SYSTEM_INSTRUCTION},
                    {"role": "user", "content": content},
                ],
            )
        except Exception as e:
            raise JudgeError(f"OpenAI API call failed: {e}") from e

        # Some proxies (e.g. tokenrun.org) force-stream even when stream=False,
        # returning a raw SSE string or a non-SDK object instead of ChatCompletion.
        try:
            text = (resp.choices[0].message.content or "") if resp.choices else ""
        except AttributeError:
            raw_str = resp if isinstance(resp, str) else getattr(resp, "text", None) or str(resp)
            text = _parse_sse_to_text(raw_str)
        try:
            scores, rationales = _common.parse_judge_json(text, request.requirements)
        except ValueError as e:
            raise JudgeError(f"{e}; raw response: {text[:500]!r}") from e
        return JudgeResponse(scores=scores, rationales=rationales, raw=text)
