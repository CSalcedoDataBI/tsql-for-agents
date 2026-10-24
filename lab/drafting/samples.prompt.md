You are writing test inputs for a probe that runs against a Microsoft Fabric Warehouse / SQL
analytics endpoint (T-SQL). For each function below, write ONE minimal statement or expression
that calls it correctly.

Rules:

- Use only literals and the function itself. No tables, no views, no variables, no temp objects.
- For a scalar function, give an expression, for example `LEN(N'abc')`. The probe wraps it in
  `SELECT <expression> AS v`.
- For a rowset function (used in FROM) or a predicate (used in WHERE), give a whole statement
  starting with `SELECT`, for example `SELECT * FROM OPENJSON(N'[1,2]')` or
  `SELECT 1 AS v WHERE REGEXP_LIKE('abc', 'a.c')`.
- For a window or aggregate function, give a whole statement over a VALUES list, for example
  `SELECT ROW_NUMBER() OVER (ORDER BY x) AS v FROM (VALUES (1),(2)) AS t(x)`.
- For a niladic function or a @@ variable, give the bare name (`CURRENT_TIMESTAMP`, `@@ROWCOUNT`).
- Do not call any function that is not in the list below, except the one being sampled and the
  usual operators. Do not use CAST or CONVERT unless they are the function being sampled.
- The statement is compiled, never executed, so it must only be valid; its result does not matter.
- If you are not sure of the arguments, still give your best call and set `confidence` to "low".

Functions (name — documentation page):

{{NAMES}}
