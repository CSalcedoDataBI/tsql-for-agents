"""Draft inputs and notes with Claude through `claude-review`, inside a hard budget.

Two kinds of drafts, both written to lab/drafting/out/ and both checked by the engine afterwards:

- samples: one minimal call per candidate (`LEN(N'abc')`, `SELECT * FROM OPENJSON(N'[1]')`). They
  are inputs for scripts/probe_fabric.py: a wrong one only produces an engine error.
- notes: Fabric traps by topic. Every claim carries the statement that proves it and the answer
  the engine should give, so `probe_fabric.py --only claims` can confirm or refute it. A note stays
  `unprobed` until then.

The prompt lists the candidate names and, when present, the probe verdicts, and the model is told to
use no other function name. scripts/check_repo.py enforces that on the output.

    python lab/drafting/draft.py samples [--batch 40]
    python lab/drafting/draft.py notes [--topics a,b]
    python lab/drafting/draft.py revise        # notes with refuted claims, once; v1 kept in out/notes-v1/
    python lab/drafting/draft.py spent

Budget: the spend is read from claude-review's own log (~/.claude-review/gasto.jsonl), counting only
calls made from this repository. The run stops before a call once BUDGET_USD is reached, and no
call is made after the promotional credit's last day.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "out"
CANDIDATES = ROOT / "catalog" / "candidates.json"
PROBE = ROOT / "catalog" / "probe" / "functions.json"
LOG = Path.home() / ".claude-review" / "gasto.jsonl"
BUDGET_USD = 35.0
LAST_DAY = dt.date(2026, 10, 26)
REPO = ROOT.name


def spent() -> float:
    if not LOG.exists():
        return 0.0
    total = 0.0
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("cwd") == REPO and row.get("usd"):
                total += float(row["usd"])
    return round(total, 4)


def call(prompt: str, schema: Path, out: Path, model: str | None) -> dict:
    if dt.date.today() > LAST_DAY:
        sys.exit(f"The promotional credit ended on {LAST_DAY}: no more calls.")
    if spent() >= BUDGET_USD:
        sys.exit(f"Budget reached: US${spent():.2f} of US${BUDGET_USD:.2f}.")
    out.parent.mkdir(parents=True, exist_ok=True)
    prompt_file = out.with_suffix(".prompt.md")
    prompt_file.write_text(prompt, encoding="utf-8", newline="\n")
    args = ["claude-review", "--prompt-file", str(prompt_file), "--schema", str(schema), "-o", str(out)]
    if model:
        args += ["--model", model]
    subprocess.run(args, check=True, cwd=ROOT, shell=sys.platform == "win32")
    prompt_file.unlink()
    print(f"{out.relative_to(ROOT).as_posix()}  (spent so far US${spent():.2f})")
    return json.loads(out.read_text(encoding="utf-8"))


def verdicts() -> dict[str, str]:
    if not PROBE.exists():
        return {}
    return {r["name"]: r["verdict"] for r in json.loads(PROBE.read_text(encoding="utf-8"))["results"]}


def samples(batch: int, model: str | None) -> None:
    template = (HERE / "samples.prompt.md").read_text(encoding="utf-8")
    known = verdicts()
    rows = [
        c
        for c in json.loads(CANDIDATES.read_text(encoding="utf-8"))["candidates"]
        if known.get(c["name"]) not in ("not_supported", "not_recognized")
    ]
    for index in range(0, len(rows), batch):
        out = OUT / "samples" / f"samples-{index // batch + 1:02d}.json"
        if out.exists():
            continue
        listing = "\n".join(f"- {c['name']} — {c['page']}" for c in rows[index : index + batch])
        call(template.replace("{{NAMES}}", listing), HERE / "samples.schema.json", out, model)
    wanted = {c["name"] for c in rows}
    merged = {
        s["name"]: s["sql"]
        for path in sorted((OUT / "samples").glob("samples-*.json"))
        for s in json.loads(path.read_text(encoding="utf-8"))["samples"]
        if s["name"] in wanted
    }
    (ROOT / "catalog" / "samples.json").write_text(
        json.dumps(dict(sorted(merged.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"catalog/samples.json: {len(merged)} samples (drafted by a model; only the probe says if they compile)")


def notes(only: list[str] | None, model: str | None) -> None:
    template = (HERE / "notes.prompt.md").read_text(encoding="utf-8")
    topics = json.loads((HERE / "topics.json").read_text(encoding="utf-8"))
    known = verdicts()
    names = [c["name"] for c in json.loads(CANDIDATES.read_text(encoding="utf-8"))["candidates"]]
    listing = "\n".join(f"- {n}: {known.get(n, 'not probed yet')}" for n in names)
    for topic in topics:
        if only and topic["id"] not in only:
            continue
        out = OUT / "notes" / f"{topic['id']}.json"
        if out.exists():
            continue
        prompt = (
            template.replace("{{TOPIC_ID}}", topic["id"])
            .replace("{{TOPIC}}", topic["title"])
            .replace("{{SCOPE}}", topic["scope"])
            .replace("{{NAMES}}", listing)
        )
        note = call(prompt, HERE / "notes.schema.json", out, model)
        # A model wrote it: it stays unprobed until probe_fabric.py --only claims has compiled it.
        note = {"status": "unprobed", "drafted_by": "claude-review", **note}
        out.write_text(json.dumps(note, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def revise(model: str | None) -> None:
    """Send each note with refuted claims back with the engine's answers; keep the first draft."""
    claims = ROOT / "catalog" / "probe" / "claims.json"
    if not claims.exists():
        sys.exit("Run `python scripts/probe_fabric.py --only claims` first.")
    template = (HERE / "revise.prompt.md").read_text(encoding="utf-8")
    known = verdicts()
    names = [c["name"] for c in json.loads(CANDIDATES.read_text(encoding="utf-8"))["candidates"]]
    listing = "\n".join(f"- {n}: {known.get(n, 'not probed yet')}" for n in names)
    refuted: dict[str, list[dict]] = {}
    for r in json.loads(claims.read_text(encoding="utf-8"))["results"]:
        if r["status"] != "confirmed":
            refuted.setdefault(r["topic"], []).append(r)
    for topic, rows in sorted(refuted.items()):
        path = OUT / "notes" / f"{topic}.json"
        first = OUT / "notes-v1" / f"{topic}.json"
        if first.exists():
            continue  # already revised once; a second round is a decision, not a loop
        first.parent.mkdir(parents=True, exist_ok=True)
        note = json.loads(path.read_text(encoding="utf-8"))
        first.write_text(json.dumps(note, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        answers = "\n".join(f"- {r['claim']}: {json.dumps(r['observed'], ensure_ascii=False)}" for r in rows)
        body = {k: v for k, v in note.items() if k not in ("status", "drafted_by", "refuted")}
        prompt = (
            template.replace("{{NOTE}}", json.dumps(body, indent=2, ensure_ascii=False))
            .replace("{{REFUTED}}", answers)
            .replace("{{NAMES}}", listing)
        )
        new = call(prompt, HERE / "notes.schema.json", path, model)
        new = {"status": "unprobed", "drafted_by": "claude-review", "revision": 2, **new}
        path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=["samples", "notes", "revise", "spent"])
    parser.add_argument("--batch", type=int, default=40)
    parser.add_argument("--topics")
    parser.add_argument("--model")
    args = parser.parse_args()
    if args.kind == "spent":
        print(f"US${spent():.2f} of US${BUDGET_USD:.2f} spent from {REPO}")
    elif args.kind == "samples":
        samples(args.batch, args.model)
    elif args.kind == "revise":
        revise(args.model)
    else:
        notes(args.topics.split(",") if args.topics else None, args.model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
