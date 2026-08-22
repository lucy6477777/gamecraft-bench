#!/usr/bin/env python3
"""Port a Godot task's rubric.json to a Web/Phaser target.

Renames engine-specific nouns using tools/rubric_port_map.yaml and swaps the
build gate. Scoring logic is never rewritten -- thresholds, the Score 0 / Score
1 / Score 0.5 structure, `agg`, the requirement ids and the score formula all
survive untouched, and that is asserted rather than assumed.

Every sentence the rules changed is written to a review file, deduplicated, so
a human reads ~60 before/after pairs instead of 1100 occurrences.

    python tools/port_rubric_to_web.py --task tasks/cardgame-autobattler \
        --out tasks-web/cardgame-autobattler
    python tools/port_rubric_to_web.py --task tasks/... --check-only
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _load_map(path: Path) -> dict:
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        sys.exit("pyyaml is required: uv pip install pyyaml")
    return yaml.safe_load(path.read_text())


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=\.)\s+", text) if s.strip()]


def apply_rules(text: str, rules: list[dict]) -> tuple[str, int]:
    """Apply term rules in order. Returns (new_text, n_substitutions)."""
    n = 0
    for rule in rules:
        src, dst = rule["from"], rule["to"]
        count = text.count(src)
        if count:
            text = text.replace(src, dst)
            n += count
    return text, n


def port(rubric: dict, spec: dict) -> tuple[dict, list[tuple[str, str]], list[str]]:
    """Return (ported_rubric, changed_sentence_pairs, leftovers)."""
    out = json.loads(json.dumps(rubric))  # deep copy
    changed: list[tuple[str, str]] = []
    leftovers: list[str] = []

    for req in out["requirements"]:
        before = req["description"]
        after, _ = apply_rules(before, spec["rules"])
        if after != before:
            for b, a in zip(_sentences(before), _sentences(after), strict=False):
                if b != a:
                    changed.append((b, a))
        req["description"] = after
        for term in spec["forbidden_after"]:
            if term in after:
                leftovers.append(f"{req['id']}: ...{_context(after, term)}...")

    bc = spec["build_check"]
    out["build_check"] = {
        "id": out["build_check"]["id"],
        "cmd": bc["cmd"],
        "description": bc["description"].strip(),
    }
    return out, changed, leftovers


def _context(text: str, term: str, w: int = 55) -> str:
    i = text.find(term)
    return re.sub(r"\s+", " ", text[max(0, i - w): i + len(term) + w])


def verify(src: dict, dst: dict) -> list[str]:
    """Structural invariants that must hold across the port."""
    errs: list[str] = []
    sid = [r["id"] for r in src["requirements"]]
    did = [r["id"] for r in dst["requirements"]]
    if sid != did:
        errs.append(f"requirement ids changed: {sid} -> {did}")
    sagg = {r["id"]: r.get("agg") for r in src["requirements"]}
    dagg = {r["id"]: r.get("agg") for r in dst["requirements"]}
    if sagg != dagg:
        errs.append("agg values changed")
    if src["score_formula"] != dst["score_formula"]:
        errs.append("score_formula changed")
    for key in ("max_demos", "max_demo_seconds", "categories"):
        if src.get(key) != dst.get(key):
            errs.append(f"{key} changed")
    for r in dst["requirements"]:
        if not r["description"].strip():
            errs.append(f"{r['id']}: empty description")

    # the formula must still evaluate against exactly these ids
    from gamecraft_bench.verifier.score import _safe_eval_formula  # noqa: PLC0415
    ones = {**{i: 1.0 for i in did}, "BUILD": 1.0}
    zeros = {**{i: 0.0 for i in did}, "BUILD": 1.0}
    gated = {**{i: 1.0 for i in did}, "BUILD": 0.0}
    try:
        if abs(_safe_eval_formula(dst["score_formula"], ones) - 1.0) > 1e-9:
            errs.append("formula does not reach 1.0 when every requirement is 1")
        if abs(_safe_eval_formula(dst["score_formula"], zeros)) > 1e-9:
            errs.append("formula is not 0.0 when every requirement is 0")
        if abs(_safe_eval_formula(dst["score_formula"], gated)) > 1e-9:
            errs.append("BUILD=0 does not zero the score")
    except Exception as exc:  # noqa: BLE001
        errs.append(f"formula failed to evaluate: {exc}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, type=Path, help="tasks/<name>")
    ap.add_argument("--out", type=Path, default=None,
                    help="destination task dir; omit with --check-only")
    ap.add_argument("--map", type=Path, default=REPO / "tools" / "rubric_port_map.yaml")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    spec = _load_map(args.map)
    src_path = args.task / "tests" / "rubric.json"
    src = json.loads(src_path.read_text())
    dst, changed, leftovers = port(src, spec)
    errs = verify(src, dst)

    name = args.task.name
    print(f"task        {name}")
    print(f"requirements {len(src['requirements'])}")
    print(f"changed sentences {len(changed)} ({len({c for c in changed})} unique)")
    print(f"leftover engine terms {len(leftovers)}")
    for line in leftovers[:10]:
        print(f"   ! {line}")
    if errs:
        print("\nSTRUCTURAL CHECK FAILED:")
        for e in errs:
            print(f"   x {e}")
        return 1
    print("structural check passed "
          "(ids, agg, formula, categories, demo caps all unchanged)")

    if args.check_only:
        return 0
    if args.out is None:
        print("--out is required unless --check-only", file=sys.stderr)
        return 2

    (args.out / "tests").mkdir(parents=True, exist_ok=True)
    (args.out / "tests" / "rubric.json").write_text(json.dumps(dst, indent=2) + "\n")

    # instruction.md: keep the design half (term-mapped), replace the whole
    # contract half with the Web contract. The split point is the heading that
    # starts the submission contract in every task in the suite.
    src_instr = (args.task / "instruction.md").read_text()
    if "## Project layout" not in src_instr:
        print("instruction.md has no '## Project layout' section", file=sys.stderr)
        return 1
    head = src_instr.split("## Project layout")[0]
    # The opening sentence is hard-wrapped, so "in Godot 4 at" can straddle a
    # newline and a plain string match misses it. Collapse the newline inside
    # the phrase before matching; the rest of the wrapping is left alone.
    head = re.sub(r"in\s+Godot\s+4\s+at", "in Godot 4 at", head)
    head = re.sub(r"No\s+(plain|naked)\s+Godot\s+grey", r"No \1 Godot grey", head)
    head, _ = apply_rules(head, spec["rules"] + spec.get("instruction_rules", []))
    # Replace the Assets section wholesale: it names mount points that only
    # exist in the Godot sandbox.
    assets = spec.get("assets_section")
    if assets and assets["heading"] in head:
        before, _, rest = head.partition(assets["heading"])
        nxt = rest.find("\n## ")
        tail = rest[nxt:] if nxt != -1 else ""
        head = before + assets["heading"] + "\n\n" + assets["body"].rstrip() + "\n" + tail
    contract = (REPO / "tools" / "web_contract.md").read_text()
    (args.out / "instruction.md").write_text(head.rstrip() + "\n\n" + contract)

    instr_left = [term for term in spec["forbidden_after"] if term in head]
    if instr_left:
        print(f"   ! instruction.md still names: {instr_left}")

    # task.toml: rename the task and drop the engine from its description.
    toml_src = (args.task / "task.toml").read_text()
    toml_src = toml_src.replace(f"gamecraft-bench/{name}", f"gamecraft-bench-web/{name}")
    toml_src, _ = apply_rules(toml_src, spec.get("instruction_rules", []))
    (args.out / "task.toml").write_text(toml_src)

    # tests/test.sh and environment/ are engine-agnostic; copy verbatim.
    shutil.copy2(args.task / "tests" / "test.sh", args.out / "tests" / "test.sh")
    (args.out / "tests" / "test.sh").chmod(0o755)
    env_src = args.task / "environment"
    if env_src.is_dir():
        shutil.copytree(env_src, args.out / "environment", dirs_exist_ok=True)

    review = args.out / "PORT_REVIEW.md"
    seen: set[tuple[str, str]] = set()
    lines = [f"# Rubric port review — {name}", "",
             "Every sentence the term rules rewrote, deduplicated. Read each pair and",
             "confirm the Web wording is exactly as strict as the Godot wording — a",
             "looser threshold here inflates every score on this task.", ""]
    for b, a in changed:
        if (b, a) in seen:
            continue
        seen.add((b, a))
        lines += [f"- **before** {b}", f"  **after**  {a}", ""]
    review.write_text("\n".join(lines))
    print(f"wrote {args.out}/tests/rubric.json")
    print(f"wrote {args.out}/instruction.md, task.toml, tests/test.sh")
    print(f"wrote {review}  ({len(seen)} pairs to review)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
