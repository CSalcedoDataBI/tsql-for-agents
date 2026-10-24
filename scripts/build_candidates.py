"""Build catalog/candidates.json from the official T-SQL function reference.

Source: MicrosoftDocs/sql-docs (CC-BY-4.0), the repository Microsoft Learn is built from, folder
docs/t-sql/functions, pinned to one commit. Each page becomes a candidate, or several when the
title names several functions ("CAST and CONVERT"). Overview pages ("String functions") are not
candidates: they give each function its categories.

A candidate is a hypothesis, not a fact about Fabric. `docs_applies_to_fabric_dw` records what the
page's "Applies to" banner claims; only scripts/probe_fabric.py may say what the engine does.

    python scripts/build_candidates.py [--commit <sha>]

Needs network access to api.github.com and raw.githubusercontent.com. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalog" / "candidates.json"
REPO = "MicrosoftDocs/sql-docs"
FOLDER = "docs/t-sql/functions/"
LEARN = "https://learn.microsoft.com/sql/t-sql/functions/"

# A T-SQL function name as it appears in a page heading: ABS, @@ROWCOUNT, $PARTITION, NEXT VALUE FOR.
NAME = re.compile(r"^[@$]{0,2}[A-Z][A-Z0-9_]*( [A-Z][A-Z0-9_]*)*$")


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read().decode("utf-8")


def latest_commit() -> str:
    return json.loads(fetch(f"https://api.github.com/repos/{REPO}/commits/live"))["sha"]


def list_pages(commit: str) -> list[str]:
    tree = json.loads(fetch(f"https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1"))
    return sorted(
        item["path"] for item in tree["tree"] if item["path"].startswith(FOLDER) and item["path"].endswith(".md")
    )


def parse(path: str, text: str) -> dict:
    front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = front.group(1) if front else ""
    title = re.search(r'^title:\s*"?(.*?)"?\s*$', meta, re.M)
    title = title.group(1).strip() if title else ""
    heading = re.search(r"^# (.+)$", text[front.end() if front else 0 :], re.M)
    heading = heading.group(1) if heading else ""
    applies = re.search(r"\[!INCLUDE \[[^\]]*\]\(\.\./\.\./includes/applies-to-version/([^)]+)\.md\)\]", text)
    applies = applies.group(1) if applies else ""
    bare = re.sub(r"\s*\(Transact-SQL\)\s*$", "", title, flags=re.I).strip()
    # "IDENTITY (Function)", "UPDATE()": the decoration is not part of the name.
    bare = re.sub(r"\s*\(Function\)|\(\)", "", bare, flags=re.I).strip()
    parts = [p.strip() for p in re.split(r",|\band\b", bare) if p.strip()]
    names = [p for p in parts if NAME.match(p)]
    # The front-matter title drops the @@ that the H1 keeps (title "CPU_BUSY", H1 "@@CPU_BUSY").
    names = [f"@@{n}" if f"@@{n}" in heading else n for n in names]
    page = path.removeprefix(FOLDER)
    # Overview pages link with bare names ("len-transact-sql.md") or full paths
    # ("../../t-sql/functions/len-transact-sql.md"); only links into this folder count.
    links = sorted(set(re.findall(r"\]\((?:(?:\.\./)*t-sql/functions/|\./)?([a-z0-9-]+\.md)(?:#[^)]*)?\)", text)))
    return {
        "page": page,
        "title": title,
        "names": names if names and len(names) == len(parts) else [],
        "applies_to": applies,
        "links": links,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", help="sql-docs commit to read (default: tip of live)")
    args = parser.parse_args()
    commit = args.commit or latest_commit()
    paths = list_pages(commit)

    def load(path: str) -> dict:
        return parse(path, fetch(f"https://raw.githubusercontent.com/{REPO}/{commit}/{path}"))

    with ThreadPoolExecutor(max_workers=8) as pool:
        pages = list(pool.map(load, paths))

    overviews = [p for p in pages if not p["names"]]
    categories: dict[str, list[str]] = {}
    for overview in overviews:
        label = re.sub(r"\s*\(Transact-SQL\)\s*$", "", overview["title"], flags=re.I)
        for link in overview["links"]:
            categories.setdefault(link, []).append(label)

    candidates = []
    for page in pages:
        for name in page["names"]:
            applies = page["applies_to"].lower()
            candidates.append(
                {
                    "name": name,
                    "page": LEARN + page["page"].removesuffix(".md"),
                    "categories": sorted(categories.get(page["page"], [])),
                    "docs_applies_to": page["applies_to"],
                    "docs_applies_to_fabric_dw": "fabricdw" in applies,
                }
            )
    candidates.sort(key=lambda c: c["name"])

    seen: dict[str, str] = {}
    for c in candidates:
        if c["name"] in seen and seen[c["name"]] != c["page"]:
            print(f"note: {c['name']} appears on {seen[c['name']]} and {c['page']}", file=sys.stderr)
        seen.setdefault(c["name"], c["page"])
    unique = {c["name"]: c for c in candidates}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "source": {
            "repository": f"https://github.com/{REPO}",
            "license": "CC-BY-4.0",
            "commit": commit,
            "folder": FOLDER,
        },
        "note": "Candidates are hypotheses taken from the documentation. Only catalog/probe/ says what Fabric does.",
        "overview_pages": sorted(p["page"] for p in overviews),
        "candidates": list(unique.values()),
    }
    OUT.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(unique)} candidates from {len(paths)} pages ({len(overviews)} overview pages) at {commit[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
