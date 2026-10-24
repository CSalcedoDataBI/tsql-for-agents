# Ficha — tsql-for-agents

> Ficha de esta herramienta. Se mantiene con las reglas internas del mantenedor: su norte es
> `FICHA.md` y el agente `experto` (`.claude/agents/experto.md`) fusiona contra ella en cada PR.
> Cambiarla exige una nueva aprobación de Cristóbal.

## Qué es

- **Qué construye y para quién:** la referencia de T-SQL de Microsoft Fabric (Warehouse y SQL
  analytics endpoint) para agentes de IA. Cada función integrada se sondea contra el motor real de
  Fabric: si existe, el error si no, y el tipo que devuelve. Las vistas y procedimientos del sistema
  salen del catálogo del propio motor. Añade las trampas de Fabric frente a SQL Server (lo no
  soportado, los tipos de datos y la collation). Es para quien escribe T-SQL de Fabric con un agente.
- **Papel** (`repo-roles`): tool (plugin de skills)
- **Gemelo público/privado:** ninguno por ahora. Hermanos de familia: `dax-for-agents`,
  `powerquery-m-for-agents` y `spark-for-agents`.

## Norte

- **Plan vigente:** [épica v0.1 — catálogo de T-SQL de Fabric verificado contra el motor](https://github.com/CSalcedoDataBI/tsql-for-agents/issues/2)
- **Lo que esta herramienta NO es:**
  - No administra Warehouses ni ejecuta cargas o diagnósticos: eso es `fabric-skills:sqldw-cli`.
  - No es Spark SQL: eso es `spark-for-agents`.
  - No es Azure SQL ni SQL Server en general: eso lo resume `MicrosoftDocs/Agent-Skills`, que se
    enlaza y no se duplica.
  - No es un tutorial de T-SQL: es una referencia que un agente consulta.

## Zonas protegidas

Lo que no se toca sin un paso del plan que lo nombre:

- Los resultados del sondeo: solo los escribe el script de sondeo. Uno a mano rompe la promesa de
  «ningún nombre inventado».
- La lista de candidatas: cada entrada cita su página de la documentación oficial.
- Los borradores escritos con un modelo siguen marcados «sin sondear» hasta que el sondeo los
  confirme.
- `LICENSE` (MIT) y la visibilidad pública del repo. Ningún nombre de workspace, servidor o
  tenant entra en el repo.

## Capa y feedback

- **Capa de nodo** (ADR 0023): `etl`
- **Skill de feedback:** `tsql-for-agents:tsql-feedback` (planeada en la v0.1)

## Check y experto

- **Check de CI requerido:** `Validate` (ruleset `main protegida` de `main`)
- **Suite de pruebas:** `python scripts/check_repo.py`
- **Runner:** GitHub (repo público). El sondeo contra Fabric corre a mano, nunca en CI.
- **Formato de tag:** `vX.Y.Z`, sacado por release-please (`release-please-config.json`).
- **Experto:** `.claude/agents/experto.md`
- **¿Plugin del directorio?:** todavía no. Se envía cuando salga de pre-release; desde entonces,
  `stable` no se toca y publicar sigue R5.
- **Partes visibles que aprueba Cristóbal:** el README de cara al público, el workspace de Fabric
  donde corre el sondeo y la salida de pre-release.

## Aprobación

Aprobada: 2026-10-23