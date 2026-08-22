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
# budget that merely fits the answer produces an empty string instead. Measured
# on gpt-5.5 with a 14-requirement rubric and 8 frames: reasoning alone wants
# 1281-2346 tokens, straddling the old 2048 ceiling -- which is why the failure
# was intermittent (1 of 6 calls returned content) rather than total, and why
# richer rubrics failed more often. 4096 clears it with headroom.
_MAX_TOKENS = max(256, int(os.environ.get("GAMECRAFT_BENCH_JUDGE_MAX_TOKENS") or 4096))
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


def _data_uri(path: Path) -> str:
    b64 = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _evenly_spaced(frames: list[Path], n: int) -> list[Path]:
    if len(frames) <= n:
        return list(frames)
    step = len(frames) / float(n)
    return [frames[min(int(i * step), len(frames) - 1)] for i in range(n)]


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
        return int(sum(f.stat().st_size for f in sel) * 4 / 3)
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
