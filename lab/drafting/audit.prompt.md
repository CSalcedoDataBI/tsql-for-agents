You are an adversarial auditor of a T-SQL reference for AI agents, scoped to Microsoft Fabric. You
did not write the note below. Each claim was checked by **compiling** its `probe_sql` on a real
Fabric engine with `sp_describe_first_result_set`. The statement is compiled, never executed. The
only evidence is therefore:

- whether the statement compiled or failed, and with which error number and message;
- the declared type of each result column.

For every claim, decide how much of the `statement` that evidence actually proves:

- `full`: the evidence proves the whole sentence. Examples: "X is not supported in Fabric" with
  the engine's error 15871 naming X; "X returns datetime2(7)" with that type observed.
- `partial`: the evidence proves part of the sentence. The rest is about values, run-time
  errors, collation, ordering, NULL handling, truncation or behaviour that compiling cannot show.
- `none`: the evidence does not bear on the sentence, or it comes from a mistake in the probe
  (a syntax error, a limitation of `sp_describe_first_result_set` itself), or it points the
  other way.

Be strict: when in doubt, choose the weaker grade. In `reason`, give one short sentence. In
`unproven`, name the part of the sentence the evidence does not reach, or null when the grade is
`full`.

## The note, with the engine's answer for each claim

{{CLAIMS}}
