#!/usr/bin/env python3
"""OpenRouter proxy that pins the serving provider and records what was spent.

WHY THIS EXISTS
codex has no way to add fields to the request body -- `model_providers.<id>`
accepts base_url / env_key / wire_api / http_headers and nothing else (checked
against the 0.150.1 binary). OpenRouter's provider pinning lives in the body
(`provider.only`), so the only place to inject it is between the two.

Pinning is not a nicety. Left to route freely, `qwen/qwen3.8-27b` can land on
Io Net, which advertises tools=False and ctx=65500 -- that single route
reproduces both known pilot failures at once (no tool calls at all, and the
silent 65k truncation) and neither announces itself. `moonshotai/kimi-k2.6` is
served at fp4, int4, fp8 and bf16 by different providers; a benchmark that
samples across those is not measuring one model.

The usage log is the other half. OpenRouter reports real cost per request at
/api/v1/generation?id=<gen>, but only if you kept the id. Every response that
carries one gets a line here; scripts/or_cost.py turns the file into a bill.

    ./or_proxy.py --port 8501 --provider AkashML --log /path/to/usage.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from aiohttp import ClientSession, ClientTimeout, web

UPSTREAM = "https://openrouter.ai/api/v1"

# `id` appears in the first SSE event of a stream and at the top of a plain
# JSON body. One match per response is enough -- it is the same generation.
_GEN_RE = re.compile(rb'"id"\s*:\s*"(gen-[^"]+)"')

# Hop-by-hop headers, plus the two that must be recomputed for the new body.
_DROP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}


class Proxy:
    def __init__(self, providers: list[str], log_path: Path, allow_fallbacks: bool):
        self.providers = providers
        self.log_path = log_path
        self.allow_fallbacks = allow_fallbacks
        self.session: ClientSession | None = None

    def _pin(self, raw: bytes) -> tuple[bytes, str | None]:
        """Inject provider preferences, if any. Returns (body, model)."""
        if not raw:
            return raw, None
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return raw, None          # not JSON: forward untouched
        if not isinstance(body, dict):
            return raw, None
        if not self.providers:
            # Free routing. OpenRouter already excludes endpoints that cannot
            # serve the request's parameters -- an agent request always carries
            # tool definitions, and measured over 12 such requests the one
            # tools=False route (Io Net, which also caps context at 65,500)
            # was never selected. What is given up is a fixed quantization:
            # tasks may land on different precisions of the same model.
            return json.dumps(body).encode(), body.get("model")
        # `only` bounds the pool; `order` says which of them we actually want.
        # They are not the same thing: with `only: [Alibaba, Novita]` alone,
        # OpenRouter picked Novita for 6 of 6 requests by its own ranking, and
        # the vendor endpoint chosen for provenance never saw traffic. `order`
        # expresses the preference; `allow_fallbacks` lets it move down the list
        # when the first is rate-limited, instead of failing the trial.
        body["provider"] = {
            "only": self.providers,
            "order": self.providers,
            "allow_fallbacks": self.allow_fallbacks,
        }
        return json.dumps(body).encode(), body.get("model")

    def _dump_bad_request(self, raw: bytes, status: int) -> str | None:
        """Keep the request that was rejected, not just the rejection.

        OpenRouter answered a codex auto-compact with `invalid_prompt` and a
        path of input[349].content -- which names the offending item but not
        its shape, and the request is the only place that shape exists. One
        file per rejection, next to the usage log.
        """
        try:
            d = self.log_path.parent / "bad_requests"
            d.mkdir(parents=True, exist_ok=True)
            f = d / f"{int(time.time())}_{status}.json"
            f.write_bytes(raw[:4_000_000])
            return str(f)
        except OSError:
            return None

    def _record(self, **fields) -> None:
        fields["ts"] = time.time()
        with self.log_path.open("a") as fh:
            fh.write(json.dumps(fields) + "\n")

    async def handle(self, request: web.Request) -> web.StreamResponse:
        raw = await request.read()
        body, model = self._pin(raw)

        headers = {k: v for k, v in request.headers.items() if k.lower() not in _DROP}
        url = f"{UPSTREAM}/{request.match_info['tail']}"

        assert self.session is not None
        upstream = await self.session.request(
            request.method, url, data=body, headers=headers,
            params=request.rel_url.query,
        )

        out = web.StreamResponse(status=upstream.status)
        # Content-Length would be wrong for a stream we forward chunk by chunk.
        for k, v in upstream.headers.items():
            if k.lower() not in _DROP:
                out.headers[k] = v
        await out.prepare(request)

        gen_id: str | None = None
        # An error body is small and is the only place the reason survives:
        # a bare 400 in the log costs an archaeology session through the
        # rollout files to learn it said "Server tool request failed".
        err = bytearray() if upstream.status >= 400 else None
        try:
            async for chunk in upstream.content.iter_any():
                if gen_id is None:
                    m = _GEN_RE.search(chunk)
                    if m:
                        gen_id = m.group(1).decode()
                if err is not None and len(err) < 2048:
                    err += chunk[: 2048 - len(err)]
                await out.write(chunk)
            await out.write_eof()
        except ConnectionResetError:
            # The agent hung up mid-stream. Upstream still billed for it, so
            # fall through to the record rather than losing the id.
            pass
        finally:
            if gen_id or upstream.status >= 400:
                dumped = (self._dump_bad_request(raw, upstream.status)
                          if upstream.status >= 400 else None)
                self._record(path=request.match_info["tail"], model=model,
                             gen_id=gen_id, status=upstream.status,
                             error=bytes(err).decode("utf-8", "replace") if err else None,
                             request_dump=dumped)
        return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--provider", action="append", default=[],
                    help="Provider name as OpenRouter spells it, e.g. AkashML. "
                         "Repeat for an ordered preference list. Omit entirely "
                         "to let OpenRouter route freely.")
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--allow-fallbacks", action="store_true",
                    help="Let OpenRouter fall back outside --provider. Off by "
                         "default: a silent reroute to a different quantization "
                         "is worse than a failed trial.")
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    proxy = Proxy(args.provider, args.log, args.allow_fallbacks)

    app = web.Application(client_max_size=1024 ** 3)
    app.router.add_route("*", "/v1/{tail:.*}", proxy.handle)

    async def _open(_):
        # No total timeout: an agent turn can legitimately generate for minutes.
        proxy.session = ClientSession(timeout=ClientTimeout(total=None, sock_read=900))

    async def _close(_):
        if proxy.session:
            await proxy.session.close()

    app.on_startup.append(_open)
    app.on_cleanup.append(_close)

    if args.provider:
        print(f">> pinning to {args.provider} (fallbacks={args.allow_fallbacks})", flush=True)
    else:
        print(">> provider: free routing (OpenRouter picks)", flush=True)
    print(f">> usage log  {args.log}", flush=True)
    # localhost only, never 0.0.0.0.
    web.run_app(app, host="127.0.0.1", port=args.port, print=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
