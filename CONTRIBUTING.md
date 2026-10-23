# Contributing

Thanks for helping. This repository is a T-SQL reference for AI agents, scoped to Microsoft Fabric,
and its one promise is that **no function name reaches an agent unless the engine backs it**.

## Report a problem

Open an [issue](https://github.com/CSalcedoDataBI/tsql-for-agents/issues) when:

- a function is catalogued wrongly (it says `not_supported` and works for you, or the reverse);
- a function is missing from `catalog/candidates.json`;
- a trap note is wrong or misleading.

Say which item you used (Warehouse or SQL analytics endpoint), the statement you ran and the
engine's answer (error number and message). Leave out workspace, server and tenant names.

## Change something

Everything enters through a pull request. The required check `Validate` must pass; it runs
`python scripts/check_repo.py` and its unit tests. Among other things it fails when a card, note
or draft names a function that is not in the verified catalogue. So:

- add a name to `catalog/candidates.json` only through `scripts/build_candidates.py`, which reads
  the official T-SQL documentation;
- never edit `catalog/probe/*.json` by hand: only `scripts/probe_fabric.py` writes them;
- a claim about Fabric needs a probe that the engine can compile.

## License

By contributing you agree that your work is released under the [MIT License](LICENSE).
