You are drafting one note of a T-SQL reference for AI agents, scoped to **Microsoft Fabric**
(Warehouse and the SQL analytics endpoint of a Lakehouse). The reader is an agent that knows SQL
Server well and keeps writing SQL Server habits into Fabric. The note lists the traps.

Topic id: {{TOPIC_ID}}
Topic: {{TOPIC}}
Scope: {{SCOPE}}

## Hard rules

1. **Only these function names exist for you.** Below is every candidate name, taken from the
   official T-SQL documentation, with what a probe against a real Fabric engine answered:
   `exists` (it compiled or failed only on arguments), `not_supported` (the engine said
   "not supported"), `not_recognized`, `unclassified` or `not probed yet`. Name no other function,
   anywhere: not in a claim, a probe or an alternative. Keywords and clauses (`OVER`, `COLLATE`,
   `WITHIN GROUP`, `AT TIME ZONE`, `TRY...CATCH`, data type names) are fine.
2. **Every claim is testable at compile time.** Give `probe_sql`, one T-SQL batch that the
   engine will only compile with `sp_describe_first_result_set` (never execute). It must use only
   literals, `VALUES` lists and system views; no user tables, no variables, no `GO`. Then say what
   the engine should answer: `compiles` (optionally with the first column's `result_type`, as
   `sp_describe_first_result_set` writes it, e.g. `varchar(8000)`, `datetime2(7)`, `int`) or
   `error` with the expected error number.
3. **The probe verdicts above are facts.** Never contradict them. When you are unsure of something
   the list does not settle, still write the claim with its probe and set `confidence` to `low`;
   the probe will settle it.
4. Contrast with SQL Server in `sql_server` only when you are sure of SQL Server's behaviour.
5. No customer, workspace, server or person names. English. Plain and short.
6. Between 6 and 14 claims. Prefer the traps that would make an agent's code fail or return a
   wrong result silently.

## Candidate names and probe verdicts

{{NAMES}}
