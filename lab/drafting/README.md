# lab/drafting — drafts written with a model

Everything under `out/` was written by Claude through `claude-review`, and **none of it is a fact
about Fabric until the engine says so.**

| Draft | What it is | Who checks it |
|---|---|---|
| `out/samples/` | one minimal call per candidate, merged into `catalog/samples.json` | `scripts/probe_fabric.py` compiles each one; a wrong sample only yields an engine error |
| `out/notes/` | Fabric traps by topic; each claim carries its `probe_sql` and the answer it expects | `scripts/probe_fabric.py --only claims` writes `catalog/probe/claims.json` |

Each note's `status` is set by `scripts/probe_fabric.py --only claims`:

| Status | Meaning |
|---|---|
| `unprobed` | at least one claim did not get the compile answer it expected (`refuted` lists them) |
| `partly_probed` | every claim got its expected answer, but the audit says some probe proves only part of its sentence (`not_fully_proven`), or the run was not on a Warehouse (`probed_on`) |
| `probed` | every claim matched, the audit grades every one `full`, and the run was on a Warehouse |

Claims the engine refuted were sent back once (`draft.py revise`, first drafts kept in
`out/notes-v1/`, which no generator reads). `draft.py audit` then graded, claim by claim, how much
of the sentence its evidence proves (`out/audit/`); the auditor is a model too, told to pick the
weaker grade when in doubt.

**What `probed` proves, and what it does not.** The probe compiles each claim's statement with
`sp_describe_first_result_set` and checks the outcome: it compiles or fails, the error number and the
first column's type. It never executes, so it cannot see a run-time value, a run-time error or
truncation. A sentence that goes beyond what the compile shows is still the model's word.
`scripts/check_repo.py` fails if a draft names a function outside `catalog/candidates.json`.

Run with `python lab/drafting/draft.py samples|notes|spent`. The spend is read from
`claude-review`'s own log, counting only calls made from this repository, and the script stops at
its budget and after the promotional credit's last day.
