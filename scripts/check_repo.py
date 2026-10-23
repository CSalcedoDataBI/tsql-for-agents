"""Repository checks that run in CI (the required `Validate` check).

- Every skills/*/SKILL.md opens with frontmatter that has `name` (matching its folder) and
  `description`.
- Every workflow job sets `timeout-minutes` and runs on `ubuntu-latest`, and every workflow
  declares `concurrency` (Actions cost rules R2, R3, R5).
- No card, note or draft names a function that is not in catalog/candidates.json. That is the
  promise of this library: no invented names.
- Every drafted note says it is `unprobed` or `probed`, and `probed` needs catalog/probe/claims.json.
- No file under catalog/ or lab/ carries a Fabric server name or a GUID (the probe target stays in
  .local/, which git ignores).
- No file links to the maintainer's private repositories or carries a path of the maintainer's
  machine: the repository is public and stands on its own.

Standard library only, so CI needs no install step. Exit code 1 lists every failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "catalog" / "candidates.json"
NOTES = ROOT / "lab" / "drafting" / "out" / "notes"

# Words that take parentheses in T-SQL without being built-in functions: clauses, operators and
# data types. A name followed by "(" that is neither here nor a candidate is an invented function.
KEYWORDS = {
    # clauses and operators
    "AS", "AND", "OR", "NOT", "IN", "EXISTS", "VALUES", "OVER", "PARTITION", "BY", "WITHIN", "GROUP",
    "ORDER", "FROM", "SELECT", "WHERE", "WITH", "ON", "JOIN", "INTO", "TABLE", "VIEW", "FUNCTION",
    "PROCEDURE", "PROC", "RETURNS", "RETURN", "EXEC", "EXECUTE", "OPTION", "ROLLUP", "CUBE", "SETS",
    "GROUPING SETS", "PIVOT", "UNPIVOT", "APPLY", "CROSS", "OUTER", "USING", "INSERT", "UPDATE",
    "DELETE", "MERGE", "CREATE", "ALTER", "DROP", "TOP", "IF", "WHILE", "BEGIN", "END", "CASE",
    "WHEN", "THEN", "ELSE", "DISTINCT", "ALL", "ANY", "SOME", "BETWEEN", "LIKE", "IS", "NULL",
    "ROWS", "RANGE", "PRECEDING", "FOLLOWING", "CURRENT", "ROW", "UNBOUNDED", "FOR", "JSON", "XML",
    "PATH", "AUTO", "RAW", "EXPLICIT", "ROOT", "BULK", "FORMAT", "CONSTRAINT", "PRIMARY", "KEY",
    "UNIQUE", "CHECK", "DEFAULT", "FOREIGN", "REFERENCES", "INDEX", "CLUSTERED", "NONCLUSTERED",
    "TRY", "CATCH", "THROW", "RAISERROR", "PRINT", "DECLARE", "SET", "COLLATE", "ZONE", "TIME",
    "WINDOW", "QUALIFY", "STATISTICS", "LIMIT", "OFFSET", "FETCH", "NEXT", "ONLY", "OUTPUT",
    # data types
    "CHAR", "VARCHAR", "NCHAR", "NVARCHAR", "BINARY", "VARBINARY", "DECIMAL", "NUMERIC", "FLOAT",
    "REAL", "DATETIME2", "DATETIMEOFFSET", "TIME", "BIT", "INT", "BIGINT", "SMALLINT", "TINYINT",
    "MONEY", "SMALLMONEY", "DATE", "DATETIME", "SMALLDATETIME", "UNIQUEIDENTIFIER", "VECTOR", "TEXT",
    "NTEXT", "IMAGE", "SQL_VARIANT", "GEOGRAPHY", "GEOMETRY", "HIERARCHYID", "ROWVERSION", "TIMESTAMP",
    "MAX", "JSONB",
}
# Not preceded by "." (schema.object) or ":" (geography::Point, a method of a type).
CALL = re.compile(r"(?<![.:\w@$#])([@$]{0,2}[A-Za-z_][A-Za-z0-9_]*)\s*\(")
SERVER = re.compile(r"[a-z0-9]{12,}-[a-z0-9]{12,}\.datawarehouse\.fabric\.microsoft\.com", re.I)
GUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)


def candidate_names() -> set[str]:
    if not CANDIDATES.exists():
        return set()
    return {c["name"].upper() for c in json.loads(CANDIDATES.read_text(encoding="utf-8"))["candidates"]}


def invented(text: str, names: set[str]) -> set[str]:
    """Called names in a piece of T-SQL that are neither candidates nor keywords."""
    found = set()
    text = re.sub(r"N?'(?:[^']|'')*'", "''", text)  # 'POINT(1 1)' is data, not a call
    for match in CALL.finditer(text):
        word = match.group(1).upper()
        if len(word) < 2 or word in KEYWORDS or word in names:
            continue
        # Lower-case words are table aliases and column lists (t(x)); a function is written in capitals.
        if not match.group(1).isupper():
            continue
        found.add(match.group(1))
    return found


def check_skills() -> list[str]:
    errors = []
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        rel = skill.relative_to(ROOT).as_posix()
        if not match:
            errors.append(f"{rel}: missing frontmatter")
            continue
        fields = dict(
            line.split(":", 1) for line in match.group(1).splitlines() if ":" in line and not line.startswith(" ")
        )
        name = fields.get("name", "").strip()
        if name != skill.parent.name:
            errors.append(f"{rel}: name '{name}' does not match folder '{skill.parent.name}'")
        if not fields.get("description", "").strip():
            errors.append(f"{rel}: empty description")
    return errors


def check_workflows() -> list[str]:
    errors = []
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = wf.read_text(encoding="utf-8")
        rel = wf.relative_to(ROOT).as_posix()
        if not re.search(r"^concurrency:", text, re.M):
            errors.append(f"{rel}: no top-level concurrency (R2)")
        jobs = len(re.findall(r"^\s+runs-on:", text, re.M))
        timeouts = len(re.findall(r"^\s+timeout-minutes:", text, re.M))
        if timeouts < jobs:
            errors.append(f"{rel}: {jobs} jobs but {timeouts} timeout-minutes (R3)")
        for runner in re.findall(r"^\s+runs-on:\s*(.+)$", text, re.M):
            if runner.strip() != "ubuntu-latest":
                errors.append(f"{rel}: runs-on {runner.strip()} (R5, and no self-hosted on a public repo)")
    return errors


def check_names() -> list[str]:
    names = candidate_names()
    errors = []
    if not names:
        return ["catalog/candidates.json: missing or empty"]
    for path in (ROOT / "catalog" / "samples.json", ROOT / "catalog" / "probe" / "functions.json"):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        keys = data.keys() if path.name == "samples.json" else [r["name"] for r in data["results"]]
        rel = path.relative_to(ROOT).as_posix()
        errors += [f"{rel}: '{k}' is not a candidate" for k in keys if k.upper() not in names]
    for note in sorted(NOTES.glob("*.json")) + sorted((NOTES.parent / "notes-v1").glob("*.json")):
        rel = note.relative_to(ROOT).as_posix()
        draft = json.loads(note.read_text(encoding="utf-8"))
        status = draft.get("status")
        if status not in ("unprobed", "probed"):
            errors.append(f"{rel}: status must be 'unprobed' or 'probed', not {status!r}")
        if status == "probed" and not (ROOT / "catalog" / "probe" / "claims.json").exists():
            errors.append(f"{rel}: 'probed' but catalog/probe/claims.json does not exist")
        for claim in draft.get("claims", []):
            for name in claim.get("functions", []):
                if name.upper() not in names:
                    errors.append(f"{rel} {claim['id']}: lists '{name}', which is not a candidate")
            text = " ".join(str(claim.get(k) or "") for k in ("statement", "probe_sql", "sql_server", "alternative"))
            for name in sorted(invented(text, names)):
                errors.append(f"{rel} {claim['id']}: calls '{name}', which is not a candidate")
    for card in sorted(ROOT.glob("skills/**/*.md")):
        rel = card.relative_to(ROOT).as_posix()
        code = " ".join(re.findall(r"```.*?```|`[^`\n]+`", card.read_text(encoding="utf-8"), re.S))
        for name in sorted(invented(code, names)):
            errors.append(f"{rel}: calls '{name}', which is not a candidate")
    return errors


def check_leaks() -> list[str]:
    errors = []
    for folder in ("catalog", "lab"):
        for path in sorted((ROOT / folder).rglob("*")):
            if not path.is_file() or path.suffix not in (".json", ".md", ".py", ".txt"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            rel = path.relative_to(ROOT).as_posix()
            if SERVER.search(text):
                errors.append(f"{rel}: contains a Fabric server name")
            if GUID.search(text):
                errors.append(f"{rel}: contains a GUID (a workspace or item id must stay in .local/)")
    return errors


# The repository is public and must stand on its own: no links into the maintainer's private
# repositories, no paths of the maintainer's machine. Built from parts so this file passes.
PRIVATE_LINK = re.compile("github" + r"\.com/CSalcedoDataBI/" + "docker" + "-lab", re.I)
LOCAL_PATH = re.compile(r"(?<![\w`])[A-Z]:\\" + r"(?:MIS-REPO|Users)\\", re.I)


def check_self_contained() -> list[str]:
    errors = []
    for path in sorted(ROOT.rglob("*")):
        parts = path.relative_to(ROOT).parts
        if not path.is_file() or parts[0] in (".git", ".local") or "__pycache__" in parts:
            continue
        if path.suffix not in (".md", ".json", ".py", ".yml", ".yaml", ".txt", ""):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        if PRIVATE_LINK.search(text):
            errors.append(f"{rel}: links to a private repository of the maintainer")
        if LOCAL_PATH.search(text):
            errors.append(f"{rel}: contains a local path of the maintainer's machine")
    return errors


def main() -> int:
    errors = check_skills() + check_workflows() + check_names() + check_leaks() + check_self_contained()
    for error in errors:
        print(f"FAIL {error}")
    if not errors:
        print("OK repo checks")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
