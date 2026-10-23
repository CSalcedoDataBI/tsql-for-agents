# tsql-for-agents — diseño inicial

*2026-10-23. Estado: borrador para la épica v0.1.*

## 1. Qué problema resuelve

Un agente que escribe T-SQL para un Warehouse de Fabric escribe T-SQL de SQL Server: usa
funciones, tipos y sintaxis que Fabric no soporta, y no lo sabe hasta que el motor falla.
`dax-for-agents`, `powerquery-m-for-agents` y `spark-for-agents` resolvieron lo mismo para su
lenguaje: el catálogo sale del motor, no de la memoria. Aquí se repite la receta con T-SQL de
Fabric (Warehouse y SQL analytics endpoint).

## 2. Fuente de verdad

T-SQL no se describe solo. No hay un `#shared` (M) ni un `SHOW FUNCTIONS` (Spark): las funciones
integradas (`LEN`, `DATEADD`…) no son filas de `sys.objects`. El método honesto tiene tres partes:

| Qué | Cómo se obtiene |
|---|---|
| (a) **Candidatas** | Una lista sacada de la documentación oficial de funciones de T-SQL (Microsoft Learn, *Functions (Transact-SQL)* y sus páginas por categoría). Cada entrada cita su página. La lista es una hipótesis, no el catálogo. |
| (b) **Sondeo** | Cada candidata se sondea contra el motor real de un Fabric Warehouse con un `SELECT` mínimo. Se guarda si existe, el error del motor si no (número y mensaje), y el tipo que devuelve con `sp_describe_first_result_set`. Solo lo que el sondeo confirma pasa a decir «existe en Fabric». |
| (c) **Objetos del sistema** | Las vistas y procedimientos del sistema salen directamente del motor: `sys.all_objects` y `sys.all_parameters`. Aquí no hay candidatas: el motor los lista. |

Cada resultado del sondeo lleva la fecha y la versión del motor (`@@VERSION`) en que se tomó,
porque Fabric cambia sin aviso.

**Autenticación y dónde corre.** Como hacen `fabric-skills:sqldw-cli` y `fabric-cli`: `az login`
con la cuenta de Entra, token con audiencia `https://database.windows.net`, y conexión TDS al
servidor `<id>.datawarehouse.fabric.microsoft.com` con el nombre del Warehouse como base de datos.
El servidor y la base se pasan por variable de entorno al correr el script, **nunca se commitean**.
El sondeo no corre en CI (necesita la sesión de Entra del mantenedor); corre a mano y su JSON se
commitea. El workspace lo elige Cristóbal: es una pregunta abierta de la épica.

**Cómo se decide sin argumentos (medido el 2026-10-23).** Todo pasa por
`sp_describe_first_result_set`, que compila y no ejecuta. Llamar la función sin argumentos basta:
195/208 = no reconocida, 15871/15868 = reconocida pero «not supported», 174/313/1076/10753 =
existe (falla solo por argumentos). Un «no soportado» solo cuenta si el mensaje nombra la función.
Las muestras de llamada (`catalog/samples.json`, redactadas con un modelo) dan el tipo de retorno y
resuelven predicados y funciones de tabla; una muestra equivocada solo produce un error.

**Primera corrida.** El workspace elegido no tiene Warehouse, solo SQL analytics endpoints, así que
la primera corrida fue sobre uno de ellos (mismo motor, solo lectura). Falta repetirla sobre un
Warehouse para ver si alguna función cambia de veredicto.

**El sondeo no escribe nada en el Warehouse.** Solo `SELECT` y
`sp_describe_first_result_set`; ninguna tabla, ningún DDL.

## 3. Antes de escribir nada (NORTE R2)

Hecho el 2026-10-23 con `gh search repos` y `gh search code`, más los plugins instalados. Lo
relevante para este repo:

- **[`MicrosoftDocs/Agent-Skills`](https://github.com/MicrosoftDocs/Agent-Skills)** (oficial,
  CC-BY-4.0) resume Azure SQL Database, Managed Instance y SQL en VM desde Microsoft Learn. **Se
  enlaza, no se duplica.** Si una nota toma texto de ahí, va con atribución y el commit de origen.
- `fabric-skills:sqldw-cli` (plugin instalado) ejecuta T-SQL contra el Warehouse, carga datos y
  diagnostica. No publica un catálogo. Este repo no ejecuta cargas ni administra nada.
- Nadie publica un catálogo de funciones de T-SQL **sondeado contra Fabric**. Ese es el hueco.

## 4. Piezas de la v0.1

1. `catalog/candidates.json`: lista de candidatas con su categoría y su página de la
   documentación.
2. `scripts/probe_fabric.py`: el sondeo (b) y la exportación (c). Escribe `catalog/probe/*.json`.
3. Un check de CI que falle si una ficha o nota nombra una función que no está en las candidatas.
4. Notas de trampas de Fabric (lo no soportado frente a SQL Server, tipos de datos, collation),
   marcadas `unprobed` hasta que el sondeo las confirme.
5. Generador de fichas (`skills/tsql-reference/generated/`), escrito solo desde el sondeo.
6. Skills `tsql-reference` y `tsql-feedback`, `.claude-plugin/` y `PRIVACY.md`.
7. Nodo de la capa `etl` (ADR 0023): `node.json`.

## 5. Salida de pre-release

Cuando el sondeo haya corrido en un workspace de Fabric, las piezas 1–6 estén en `main` y una
prueba de invención (como la de `powerquery-m-for-agents`) muestre la mejora, se quita el aviso de
pre-release y se propone a Cristóbal enviarlo al directorio de plugins.
