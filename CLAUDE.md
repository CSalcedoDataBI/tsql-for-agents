# Agent instructions

This repository is **public and in pre-release**. Write every issue and commit with that in mind:
no client names, no real engagements, no credentials, no workspace or server names, and nothing
from private repositories.

It follows [NORTE](https://github.com/CSalcedoDataBI/docker-lab/blob/main/NORTE.md). The north for
every PR is [FICHA.md](FICHA.md), and `.claude/agents/experto.md` merges against it.

## Rules specific to this repo

- **Never add a function name to anything an agent reads unless it is in the candidate list**
  (`catalog/candidates.json`), and never call it "supported in Fabric" until a probe against a
  Fabric Warehouse says so. This library exists to stop invention, so it cannot contain any.
- **Probe results are written only by the probe script.** Never edit one by hand; write a note
  instead.
- **Drafts written with a model are marked `unprobed`** until a probe confirms every claim in them.
- **Every number in the README is counted from the tree**, not typed. Until a check backs a
  number, do not write it.
- **CI runs on GitHub runners, never on a self-hosted one.** The repo is public, and a self-hosted
  runner would execute fork PRs on the maintainer's machine (DIRECTRICES, RUNSEC A exception).
- **The probe never runs in CI.** It needs a Fabric workspace and an Entra sign-in, which stay on
  the maintainer's machine. Its JSON output is committed.
- The repository is in English. Specs and ADRs under `docs/` are in Spanish, as in dax-for-agents.
