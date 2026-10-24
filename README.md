# tsql-for-agents

> **Pre-release.** This repository is public from day one, but nothing in it is ready to install
> yet. The function catalogue has not been probed against a Fabric engine, and there is no plugin
> to add. Watch the repository or follow the
> [v0.1 epic](https://github.com/CSalcedoDataBI/tsql-for-agents/issues/2) if you want to know when
> that changes.

The T-SQL reference for AI agents, scoped to **Microsoft Fabric**: the Warehouse and the SQL
analytics endpoint of a Lakehouse. Every built-in function is **probed against the real engine**
instead of typed from memory: whether it exists in Fabric, the error it raises if it does not, and
the type it returns. System views and procedures come straight from the engine's own catalog.

It is the sibling of [dax-for-agents](https://github.com/CSalcedoDataBI/dax-for-agents),
[powerquery-m-for-agents](https://github.com/CSalcedoDataBI/powerquery-m-for-agents) and
[spark-for-agents](https://github.com/CSalcedoDataBI/spark-for-agents), and it follows the same
rule: **an agent never reads a function name that did not come from the engine.**

## Why probing

T-SQL does not describe itself. Built-in scalar functions such as `LEN` or `DATEADD` are not rows in
`sys.objects`, so there is no `SHOW FUNCTIONS` to export. The honest method has three steps:

1. A list of **candidates** taken from the official T-SQL function documentation.
2. Each candidate is **probed** on a Fabric engine with a minimal `SELECT`, through
   `sp_describe_first_result_set`, which compiles the statement and never runs it. The result
   records whether the name exists, the engine's error if it does not (`not supported` is not the
   same as `not recognized`), and the returned type. The first run used a SQL analytics endpoint;
   a Warehouse run is still to come.
3. System views and procedures come directly from `sys.all_objects` and `sys.all_parameters`.

## What it will contain

| Piece | Source | Status |
|---|---|---|
| Candidate list of built-in functions ([`catalog/candidates.json`](catalog/candidates.json)) | official T-SQL function reference (`MicrosoftDocs/sql-docs`, CC-BY-4.0, pinned commit) | first version |
| Probe results ([`catalog/probe/functions.json`](catalog/probe/functions.json)) | `sp_describe_first_result_set` on a minimal `SELECT`, compiled on a Fabric SQL analytics endpoint, never executed | first run |
| System views and procedures ([`catalog/probe/system_objects.json`](catalog/probe/system_objects.json)) | `sys.all_objects` + `sys.all_parameters` on the engine | first run |
| Fabric traps (unsupported vs SQL Server, types, collation) | drafts in [`lab/drafting/`](lab/drafting/), each claim with its own probe | drafts |
| `tsql-feedback` skill | report a wrong or missing card as a public issue | planned |

## Not in scope

- Administering Warehouses, running loads or diagnosing queries. That is the `sqldw-cli` skill of
  the Fabric skills plugin.
- Spark SQL. That is [spark-for-agents](https://github.com/CSalcedoDataBI/spark-for-agents).
- Azure SQL, SQL Server or Fabric SQL database in general. Microsoft's own
  [Agent-Skills](https://github.com/MicrosoftDocs/Agent-Skills) summarises Azure SQL from Microsoft
  Learn; this repo links to it instead of duplicating it.

## License

[MIT](LICENSE).
