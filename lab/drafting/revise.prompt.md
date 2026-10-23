You drafted the note below for a T-SQL reference for AI agents, scoped to Microsoft Fabric. Every
claim's `probe_sql` was then compiled on a real Fabric engine with `sp_describe_first_result_set`
(compiled, never executed). Some claims were **refuted**: the engine answered differently from
`expect`. The engine is right; the note must change.

For each refuted claim, do exactly one of these:

1. **Fix it**: rewrite `statement`, `probe_sql` and `expect` so they say what the engine showed.
   Do not keep a statement that the evidence contradicts.
2. **Drop it** when the claim is about run-time behaviour that compiling cannot show (a value, a
   run-time error, truncation, a file that must exist). Remove it from `claims`.

Keep every confirmed claim exactly as it is. Keep the same rules as before: use only function
names from the candidate list below; probes use only literals, `VALUES` lists and system views; no
customer, workspace, server or person names. Return the whole revised note.

## The note

{{NOTE}}

## What the engine answered for each refuted claim

{{REFUTED}}

## Candidate names and probe verdicts

{{NAMES}}
