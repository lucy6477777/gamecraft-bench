"""A judge that never answers must not look like a game that scored zero.

This is the defect the repo hit twice for real: an artifact scored 0.000 with
four failed judge calls and 0.481 when the identical bytes were judged again.
The cause was that a failed call wrote 0.0 for every requirement of that demo,
and a fabricated 0.0 is indistinguishable from an observed one once it is
inside max()/mean().

Runs score_project end to end with build, replay and frame sampling stubbed,
so the only live logic is the part that decides what a failure means.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from gamecraft_bench.verifier import score as S
from gamecraft_bench.verifier.judges.base import JudgeError, JudgeResponse

RUBRIC = {
    "score_formula": "BUILD * ((M1 + V1) / 2)",
    "build_check": {"id": "BUILD", "cmd": "true", "description": "stub"},
    "requirements": [
        {"id": "M1", "description": "a mechanic", "agg": "max"},
        {"id": "V1", "description": "a visual",   "agg": "mean"},
    ],
}


class FlakyJudge:
    """Answers 0.8 for every demo except the one it is told to fail on."""
    name, model = "flaky", "stub"

    def __init__(self, fail_on: set[str]):
        self.fail_on = fail_on

    def score(self, request):
        if request.demo_id in self.fail_on:
            raise JudgeError("simulated: empty response from judge")
        return JudgeResponse(scores={"M1": 0.8, "V1": 0.8},
                             rationales={"M1": "", "V1": ""}, raw="{}")


def _setup(tmp: Path, n_demos: int) -> tuple[Path, Path, Path]:
    project = tmp / "game"; (project / "demo_outputs").mkdir(parents=True)
    for i in range(1, n_demos + 1):
        (project / "demo_outputs" / f"{i:02d}_demo.json").write_text("{}")
    rubric = tmp / "rubric.json"; rubric.write_text(json.dumps(RUBRIC))
    out = tmp / "out"; out.mkdir()

    S._run_build_check = lambda spec, od: (True, "stub build ok")
    S._resolve_replay = lambda engine=None: (
        lambda **kw: type("R", (), {"duration_seconds": 5.0})(), "stub")
    S._sample_frames = lambda mp4, d, **kw: [Path("frame.png")]
    return project, rubric, out


def _run(tmp: Path, n_demos: int, fail_on: set[str]):
    project, rubric, out = _setup(tmp, n_demos)
    S._JUDGE_MAX_ATTEMPTS = 1          # do not wait through five backoffs
    return S.score_project(project_dir=project, rubric_path=rubric,
                           output_dir=out, judge=FlakyJudge(fail_on)), out


def main() -> int:
    import tempfile
    failures: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    # --- one demo of three fails ------------------------------------------
    print("\n3 demos, judge fails on 02_demo:")
    with tempfile.TemporaryDirectory() as td:
        res, out = _run(Path(td), 3, {"02_demo"})
        bd = json.loads((out / "breakdown.json").read_text())
        m1 = next(r for r in bd["requirements"] if r["id"] == "M1")
        v1 = next(r for r in bd["requirements"] if r["id"] == "V1")

        check("failed demo absent from per_demo",
              "02_demo" not in m1["per_demo"], str(m1["per_demo"]))
        check("mean not dragged down by a fabricated zero",
              abs(v1["aggregated"] - 0.8) < 1e-9,
              f"V1={v1['aggregated']} (a fabricated 0 would give 0.533)")
        check("reward reflects only what was judged",
              abs(res.reward - 0.8) < 1e-9, f"reward={res.reward}")
        check("coverage recorded", bd["judge_coverage"] == {
              "demos_total": 3, "demos_judged": 2,
              "demos_unjudged": ["02_demo"], "complete": False},
              json.dumps(bd["judge_coverage"]))
        check("sentinel written", (out / "JUDGE_INCOMPLETE.json").is_file())
        check("contributing count exposed", m1["demos_contributing"] == 2,
              str(m1.get("demos_contributing")))

    # --- every demo fails: the number is meaningless, say so --------------
    print("\n3 demos, judge fails on all of them:")
    with tempfile.TemporaryDirectory() as td:
        res, out = _run(Path(td), 3, {"01_demo", "02_demo", "03_demo"})
        bd = json.loads((out / "breakdown.json").read_text())
        check("reward is 0 but flagged, not silently reported",
              res.reward == 0.0 and (out / "JUDGE_INCOMPLETE.json").is_file(),
              f"reward={res.reward}")
        check("coverage says nothing was judged",
              bd["judge_coverage"]["demos_judged"] == 0)

    # --- nothing fails: unchanged behaviour, no sentinel -------------------
    print("\n3 demos, judge answers every call:")
    with tempfile.TemporaryDirectory() as td:
        res, out = _run(Path(td), 3, set())
        bd = json.loads((out / "breakdown.json").read_text())
        check("reward unchanged", abs(res.reward - 0.8) < 1e-9, f"{res.reward}")
        check("no sentinel", not (out / "JUDGE_INCOMPLETE.json").exists())
        check("coverage complete", bd["judge_coverage"]["complete"] is True)

    print(f"\n{'ALL PASS' if not failures else str(len(failures)) + ' FAILED: ' + ', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
