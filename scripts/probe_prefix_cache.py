"""Prefix-caching correctness probe for the hybrid-GDN Qwen3.8-27B.

The risky path is mamba/GDN recurrent-state restoration at cached block
boundaries: if 'align' mode restores state wrongly, the model loses detail
buried deep inside the cached prefix. So the question is answerable only by
recalling a fact from the middle of the prefix, not from the fresh suffix.
"""
import json, time, urllib.request

URL = "http://127.0.0.1:8038/v1/chat/completions"

# Deterministic haystack: 300 unique key/value lines the model must recall.
lines = [f"KEY_{i:03d} = {(i * 7919) % 100000:05d}" for i in range(300)]
PREFIX = ("Below is a configuration dump. Memorise it; you will be asked "
          "about individual entries.\n\n" + "\n".join(lines) + "\n\nEnd of dump.")

def ask(key_idx, tag):
    body = {
        "model": "qwen38-27b",
        "messages": [
            {"role": "user",
             "content": PREFIX + f"\n\nWhat is the value of KEY_{key_idx:03d}? "
                                 "Reply with the 5-digit value only."},
        ],
        "temperature": 0, "max_tokens": 64,
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer x"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    dt = time.time() - t0
    msg = d["choices"][0]["message"]
    text = (msg.get("content") or "").strip()
    u = d["usage"]
    truth = f"{(key_idx * 7919) % 100000:05d}"
    ok = truth in text
    print(f"{tag:<28} key={key_idx:03d} truth={truth} "
          f"got={text[:40]!r:<12} {'OK' if ok else 'WRONG'}  "
          f"prompt={u['prompt_tokens']} {dt:.1f}s")
    return ok

print("--- cold (nothing cached) ---")
r1 = ask(137, "1 cold")
print("--- warm (identical request) ---")
r2 = ask(137, "2 warm / full hit")
print("--- partial hit (same prefix, new question) ---")
r3 = ask(42, "3 warm / partial hit")
r4 = ask(288, "4 warm / partial hit")
print()
print("ALL CORRECT" if all([r1, r2, r3, r4]) else "MISMATCH -> prefix caching suspect")
