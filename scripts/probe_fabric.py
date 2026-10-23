"""Probe every candidate against a real Fabric Warehouse or SQL analytics endpoint.

Two outputs, both written only by this script:

- catalog/probe/functions.json: for each name in catalog/candidates.json, what the engine says
  when it compiles a minimal SELECT that calls it.
- catalog/probe/system_objects.json: the engine's own list of system views, functions and
  procedures, with their parameters (sys.all_objects + sys.all_parameters).

How a function is probed. Every statement goes through sp_describe_first_result_set, which
compiles the statement and never runs it: nothing is read, nothing is written, and the call costs
a compile, not a query. No arguments are needed to tell whether a function exists, because the
engine answers a call with no arguments differently for each case:

    SELECT NOPE()          -> 195   'NOPE' is not a recognized built-in function name
    SELECT * FROM NOPE()   -> 208   Invalid object name 'NOPE'
    SELECT ENCRYPTBYKEY()  -> 15871 FUNCTION 'ENCRYPTBYKEY' is not supported
    SELECT LEN()           -> 174   The len function requires 1 argument(s)
    SELECT ROW_NUMBER()    -> 10753 The function 'ROW_NUMBER' must have an OVER clause
    SELECT GETDATE()       -> compiles, and the result type comes back (datetime)

Each candidate is tried as a scalar call, then as a rowset call (FROM), then without parentheses
(CURRENT_TIMESTAMP), and the first answer that decides is kept. Every attempt and every engine
error is saved as it came, so the verdict can be re-read and challenged. An answer the table
below does not know is saved as `unclassified`, never guessed.

The return type of a function that needs arguments needs a sample call. catalog/samples.json
(name -> expression, or a whole SELECT for rowset functions and predicates) supplies them. A sample
is an input, so a wrong one only produces an error; a sample that compiles proves the name exists.

Where it connects. The target lives in .local/fabric.json, which git ignores, so no workspace,
server or database name ever reaches this public repository:

    {"server": "<id>.datawarehouse.fabric.microsoft.com", "database": "<item name>",
     "item_kind": "warehouse" | "sql_analytics_endpoint"}

Sign-in is the Azure CLI session (`az login`), with a token for https://database.windows.net/,
the same route the Fabric skills use. This script never runs in CI.

    python scripts/probe_fabric.py [--only functions|objects|claims] [--names LEN,GETDATE] [--batch 25]

`--only claims` compiles the probe of every claim in lab/drafting/out/notes/ and writes
catalog/probe/claims.json with confirmed / refuted / partly for each.

Needs pyodbc and Microsoft ODBC Driver 17 or 18 for SQL Server.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "catalog" / "candidates.json"
SAMPLES = ROOT / "catalog" / "samples.json"
PROBE = ROOT / "catalog" / "probe"
TARGET = ROOT / ".local" / "fabric.json"
NOTES = ROOT / "lab" / "drafting" / "out" / "notes"

# Engine error numbers -> what they say about the called name.
# NOT_RECOGNIZED and NOT_SUPPORTED only count when the message names the probed function: in
# `NEXT VALUE FOR dbo.s` the engine answers "FUNCTION 'dbo' is not supported", which is about dbo.
NOT_RECOGNIZED = {195, 208}
NOT_SUPPORTED = {15868, 15871}
# Recognised, but called with the wrong arguments or outside its context (140: UPDATE() outside a
# trigger; 13822: OPENROWSET(BULK) parsed and tried to open the file).
EXISTS = {140, 174, 189, 313, 1076, 8144, 10753, 10755, 4113, 4114, 4115, 8116, 8117, 10754, 10757, 10758, 13822}
# Wrong call shape: try the next form before deciding (207: a bare name read as a column).
WRONG_FORM = {102, 156, 207, 4121}

SQL_COPT_SS_ACCESS_TOKEN = 1256
ERROR = re.compile(r"\[SQL Server\](.*?) \((\d+)\)(?: \(SQL\w+\))?(?:;|$)")


class Throttled(RuntimeError):
    pass


def connect(target: dict):
    import pyodbc

    token = subprocess.run(
        "az account get-access-token --resource https://database.windows.net/ --query accessToken -o tsv",
        shell=True,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    raw = token.encode("utf-16-le")
    drivers = [d for d in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server") if d in pyodbc.drivers()]
    if not drivers:
        sys.exit("No Microsoft ODBC Driver 17 or 18 for SQL Server installed.")
    return pyodbc.connect(
        f"Driver={{{drivers[0]}}};Server={target['server']},1433;Database={target['database']};"
        "Encrypt=yes;TrustServerCertificate=no",
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: struct.pack(f"<I{len(raw)}s", len(raw), raw)},
        timeout=60,
    )


def scrub(text: str, target: dict) -> str:
    for secret in (target.get("server", ""), target.get("database", "")):
        if secret:
            text = text.replace(secret, "<target>")
    return text


def errors_of(exc: Exception, target: dict) -> list[dict]:
    message = str(exc.args[1] if len(exc.args) > 1 else exc)
    found = [{"number": int(n), "message": scrub(m.strip(), target)} for m, n in ERROR.findall(message)]
    if any(w in message.lower() for w in ("throttl", "capacity", "too many requests")):
        raise Throttled(scrub(message, target))
    return found or [{"number": None, "message": scrub(message, target)}]


def describe(cursor, sql: str, target: dict) -> dict:
    import pyodbc

    try:
        rows = cursor.execute("EXEC sp_describe_first_result_set @tsql = ?", sql).fetchall()
        return {"sql": sql, "ok": True, "result_types": [row.system_type_name for row in rows]}
    except pyodbc.Error as exc:
        return {"sql": sql, "ok": False, "errors": errors_of(exc, target)}


def verdict_of(attempt: dict, name: str) -> str | None:
    if attempt["ok"]:
        return "exists"
    word = name.lstrip("@$").split()[0].lower()
    errors = [e for e in attempt["errors"] if e["number"] not in (11501, 11529)]
    numbers = {e["number"] for e in errors}
    about = {e["number"] for e in errors if word in e["message"].lower()}
    if about & NOT_SUPPORTED:
        return "not_supported"
    if numbers & EXISTS:
        return "exists"
    if about & NOT_RECOGNIZED or numbers & WRONG_FORM:
        return None  # try the next form
    return "unclassified"


def named_not_recognized(attempt: dict, name: str) -> bool:
    word = name.lstrip("@$").split()[0].lower()
    return any(e["number"] in NOT_RECOGNIZED and word in e["message"].lower() for e in attempt.get("errors", []))


def forms(name: str) -> list[str]:
    if name.startswith("@@"):
        return [f"SELECT {name}"]
    if " " in name:
        return []  # NEXT VALUE FOR, OPENROWSET BULK: syntax, not a call; probed by hand
    return [f"SELECT {name}()", f"SELECT * FROM {name}()", f"SELECT {name}"]


def probe_one(cursor, name: str, sample: str | None, target: dict) -> dict:
    result: dict = {"name": name, "attempts": []}
    decided = None
    for sql in forms(name):
        attempt = describe(cursor, sql, target)
        result["attempts"].append(attempt)
        decided = verdict_of(attempt, name)
        if decided:
            break
    if decided is None and result["attempts"]:
        recognized = not any(named_not_recognized(a, name) for a in result["attempts"])
        decided = "unclassified" if recognized else "not_recognized"
    # A sample is a whole statement ("SELECT * FROM OPENJSON(...)") or an expression. It gives the
    # return type, and it settles names the call shapes above cannot (predicates, NEXT VALUE FOR):
    # a statement that compiles proves the name exists.
    if sample and decided != "not_supported":
        sql = sample if sample.lstrip().upper().startswith(("SELECT", "WITH")) else f"SELECT {sample} AS v"
        result["sample"] = describe(cursor, sql, target)
        if result["sample"]["ok"]:
            decided = "exists"
        else:
            # The sample has the right shape, so its answer beats the guessed shapes above.
            from_sample = verdict_of(result["sample"], name)
            if from_sample in ("exists", "not_supported"):
                decided = from_sample
            elif decided in (None, "unclassified") and named_not_recognized(result["sample"], name):
                decided = "not_recognized"
            elif decided is None:
                decided = "unclassified"
    result["verdict"] = decided or "not_probed"
    types = [t for a in result["attempts"] + [result.get("sample", {})] if a.get("ok") for t in a["result_types"]]
    if types:
        result["return_type"] = types[-1]
    return result


def engine_of(cursor, target: dict) -> dict:
    version = cursor.execute("SELECT @@VERSION").fetchone()[0]
    lines = [line.strip() for line in version.splitlines() if line.strip()]
    return {"version": lines[0], "build_date": lines[1] if len(lines) > 1 else None, "item_kind": target.get("item_kind")}


def probe_functions(cursor, target: dict, names: list[str] | None, batch: int, pause: float) -> None:
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    samples = json.loads(SAMPLES.read_text(encoding="utf-8")) if SAMPLES.exists() else {}
    wanted = [c["name"] for c in candidates["candidates"] if not names or c["name"] in names]
    out = PROBE / "functions.json"
    previous = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"results": []}
    results = {r["name"]: r for r in previous["results"]}
    stopped = None
    for start in range(0, len(wanted), batch):
        try:
            for name in wanted[start : start + batch]:
                results[name] = probe_one(cursor, name, samples.get(name), target)
        except Throttled as exc:
            stopped = f"stopped at {name}: {exc}"
            print(stopped, file=sys.stderr)
            break
        print(f"{min(start + batch, len(wanted))}/{len(wanted)}")
        time.sleep(pause)
    document = {
        "probed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": engine_of(cursor, target),
        "candidates_commit": candidates["source"]["commit"],
        "method": "sp_describe_first_result_set on a minimal SELECT; compiled, never executed",
        "complete": stopped is None and all(c["name"] in results for c in candidates["candidates"]),
        "results": sorted(results.values(), key=lambda r: r["name"]),
    }
    write(out, document)
    counts: dict[str, int] = {}
    for r in document["results"]:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(json.dumps(counts, sort_keys=True))


def probe_objects(cursor, target: dict) -> None:
    objects = cursor.execute(
        """
        SELECT o.object_id, SCHEMA_NAME(o.schema_id) AS schema_name, o.name, o.type, o.type_desc
        FROM sys.all_objects AS o
        WHERE o.is_ms_shipped = 1 AND SCHEMA_NAME(o.schema_id) IN ('sys', 'INFORMATION_SCHEMA')
        """
    ).fetchall()
    params = cursor.execute(
        """
        SELECT p.object_id, p.parameter_id, p.name, TYPE_NAME(p.user_type_id) AS type_name,
               p.max_length, p.precision, p.scale, p.is_output
        FROM sys.all_parameters AS p
        JOIN sys.all_objects AS o ON o.object_id = p.object_id
        WHERE o.is_ms_shipped = 1 AND SCHEMA_NAME(o.schema_id) IN ('sys', 'INFORMATION_SCHEMA')
        """
    ).fetchall()
    by_object: dict[int, list[dict]] = {}
    for p in params:
        by_object.setdefault(p.object_id, []).append(
            {
                "position": p.parameter_id,
                "name": p.name or None,
                "type": p.type_name,
                "max_length": p.max_length,
                "precision": p.precision,
                "scale": p.scale,
                "is_output": bool(p.is_output),
            }
        )
    document = {
        "probed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": engine_of(cursor, target),
        "source": "sys.all_objects + sys.all_parameters, is_ms_shipped = 1, schemas sys and INFORMATION_SCHEMA",
        "objects": sorted(
            (
                {
                    "schema": o.schema_name,
                    "name": o.name,
                    "type": o.type.strip(),
                    "type_desc": o.type_desc,
                    "parameters": sorted(by_object.get(o.object_id, []), key=lambda p: p["position"]),
                }
                for o in objects
            ),
            key=lambda o: (o["schema"], o["name"]),
        ),
    }
    write(PROBE / "system_objects.json", document)
    print(f"{len(document['objects'])} system objects, {len(params)} parameters")


def probe_claims(cursor, target: dict, pause: float) -> None:
    """Compile every claim's probe_sql from the drafted notes and compare with what it expects."""
    results = []
    for note in sorted(NOTES.glob("*.json")):
        draft = json.loads(note.read_text(encoding="utf-8"))
        for claim in draft["claims"]:
            observed = describe(cursor, claim["probe_sql"], target)
            expect = claim["expect"]
            numbers = {e["number"] for e in observed.get("errors", [])} - {11501, 11529}
            if expect["outcome"] == "compiles":
                status = "confirmed" if observed["ok"] else "refuted"
                wanted = (expect.get("result_type") or "").replace(" ", "").lower()
                got = (observed.get("result_types") or [""])[0] or ""
                if observed["ok"] and wanted and got.replace(" ", "").lower() != wanted:
                    status = "refuted"
            else:
                status = "refuted" if observed["ok"] else (
                    "confirmed" if expect.get("error_number") in numbers or not expect.get("error_number") else "partly"
                )
            results.append({"topic": draft["topic"], "claim": claim["id"], "status": status, "observed": observed})
        time.sleep(pause)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    # A note becomes `probed` only when the engine confirmed every one of its claims.
    for note in sorted(NOTES.glob("*.json")):
        draft = json.loads(note.read_text(encoding="utf-8"))
        mine = [r for r in results if r["topic"] == draft["topic"]]
        refuted = [r["claim"] for r in mine if r["status"] != "confirmed"]
        draft["status"] = "probed" if mine and not refuted else "unprobed"
        draft["refuted"] = refuted
        write(note, draft)
    write(
        PROBE / "claims.json",
        {
            "probed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "engine": engine_of(cursor, target),
            "method": "each claim's probe_sql through sp_describe_first_result_set; compiled, never executed",
            "counts": counts,
            "results": results,
        },
    )
    print(json.dumps(counts, sort_keys=True))


def write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=["functions", "objects", "claims"])
    parser.add_argument("--names", help="comma-separated candidate names (default: all)")
    parser.add_argument("--batch", type=int, default=25, help="calls between pauses")
    parser.add_argument("--pause", type=float, default=2.0, help="seconds between batches")
    args = parser.parse_args()
    if not TARGET.exists():
        sys.exit(f"Missing {TARGET.relative_to(ROOT)}: see the docstring for its shape.")
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    cursor = connect(target).cursor()
    names = [n.strip() for n in args.names.split(",")] if args.names else None
    if args.only in (None, "functions"):
        probe_functions(cursor, target, names, args.batch, args.pause)
    if args.only in (None, "objects"):
        probe_objects(cursor, target)
    if args.only == "claims":
        probe_claims(cursor, target, args.pause)
    return 0


if __name__ == "__main__":
    sys.exit(main())
