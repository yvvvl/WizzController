# WizZ Desktop documentation guide

Este documento define la estructura documental oficial de WizZ Desktop. Su
objetivo es que mantenedores y futuras sesiones de ChatGPT/Codex encuentren
una única fuente para cada tipo de información sin perder evidencia
histórica.

## Fuentes canónicas

La prioridad documental es:

1. `docs/adr/` para decisiones arquitectónicas aceptadas;
2. `docs/codex/PROJECT_CONTEXT.md` para el estado actual;
3. `docs/codex/queries/` para evidencia, investigaciones y resultados;
4. `docs/codex/plans/` para trabajo previsto o ya ejecutado;
5. `docs/third-party/` para evidencia externa, permisos y atribución;
6. `docs/archive/` para material reemplazado que ya no es canónico.

El código y la configuración efectiva prevalecen si un documento histórico
describe una implementación anterior. La discrepancia debe corregirse en
`PROJECT_CONTEXT.md` o mediante un ADR, no reescribiendo evidencia histórica
sin explicación.

## Estructura

```text
docs/
├── adr/
├── codex/
│   ├── PROJECT_CONTEXT.md
│   ├── DOCUMENTATION_GUIDE.md
│   ├── queries/
│   └── plans/
├── third-party/
└── archive/
```

`README.md`, `CHANGELOG.md` y `THIRD_PARTY_NOTICES.md` permanecen en la raíz
del repositorio porque son artefactos públicos o de distribución. La copia de
avisos bajo `licenses/` existe para packaging y no es un duplicado editorial.

## ADR

Ruta: `docs/adr/NNNN-topic.md`.

Crear un ADR cuando una decisión:

- define ownership o una frontera entre componentes;
- cambia contratos de largo plazo;
- elige o rechaza una estrategia arquitectónica;
- establece una restricción que futuras fases no deben revertir
  incidentalmente.

Un ADR contiene contexto, decisión, consecuencias, límites y alternativas
rechazadas. No contiene logs, comandos ejecutados, resultados de una suite
concreta ni un plan paso a paso.

Estados permitidos:

- `Draft`;
- `Accepted`;
- `Superseded`.

Encabezado recomendado:

```markdown
# ADR NNNN: Title

- Status: Accepted
- Date: YYYY-MM-DD
- Scope: ...
```

Cuando una decisión cambia, crear un nuevo ADR y marcar el anterior como
`Superseded`, enlazando ambos. No borrar la decisión anterior.

## Project Context

Ruta: `docs/codex/PROJECT_CONTEXT.md`.

Es la fotografía vigente del proyecto. Debe responder:

- qué está estable, implementado, experimental o pendiente;
- cuál es la arquitectura y quién posee cada responsabilidad;
- cuáles son las ramas relevantes;
- qué decisiones no deben revertirse;
- cuál es el roadmap y cuáles son los riesgos actuales.

No debe acumular comandos, diffs ni resultados históricos de cada fase. Esa
evidencia pertenece a `queries/`. Al cerrar una fase, actualizar sólo el
estado, los límites y los próximos pasos que sigan vigentes.

## Queries y reportes

Ruta y formato obligatorio:

```text
docs/codex/queries/YYYY-MM-DD-NN-topic.md
```

`NN` es una secuencia de dos dígitos dentro de la fecha. El topic usa
kebab-case y describe el contenido, no el nombre del agente.

Crear una query para:

- investigación técnica;
- revisión arquitectónica;
- auditoría interna;
- reporte final de una fase;
- evidencia de validación y próximos pasos.

Debe registrar contexto, evidencia, conclusiones, limitaciones y próximos
pasos. Puede conservar comandos y resultados porque funciona como registro
histórico.

Estados permitidos:

- `Investigation`;
- `Completed`;
- `Archived`.

Encabezado recomendado:

```markdown
# Topic

Status: Completed

Fecha: YYYY-MM-DD
```

## Planes

Ruta y formato:

```text
docs/codex/plans/YYYY-MM-DD-topic.md
```

Crear un plan antes de una fase de implementación o ejecución cuando sea
necesario enumerar tareas, archivos, contratos, pruebas o checkpoints. Los
checklists manuales también son planes.

Cuando la fase termina, el plan permanece como evidencia histórica con
`Status: Completed`; el resultado y la validación final van en una query. No
convertir el plan en reporte reescribiendo sus pasos originales.

Estados permitidos:

- `Planned`;
- `In Progress`;
- `Completed`;
- `Archived`.

## Third-party

Ruta recomendada:

```text
docs/third-party/YYYY-MM-DD-project-topic.md
```

Aquí viven:

- auditorías de repositorios y dependencias;
- revisión de licencias y permisos;
- evidencia de colaboración externa;
- borradores de créditos;
- restricciones de copia o redistribución.

Un documento third-party debe congelar la fuente o revisión auditada, separar
hechos de inferencias y dejar explícito si el permiso/licencia sigue
pendiente. Los avisos distribuibles continúan en `THIRD_PARTY_NOTICES.md`.

## Archive

Ruta recomendada:

```text
docs/archive/YYYY-MM-DD-topic.md
```

Mover aquí documentos reemplazados, duplicados o generados para una forma de
trabajo que ya no es canónica. Añadir:

```markdown
Status: Archived
```

y una explicación breve de qué documento los reemplaza. Archivar no significa
eliminar evidencia.

## Referencias

Todas las rutas documentales son relativas a la raíz del repositorio y usan
`/`:

```text
docs/codex/PROJECT_CONTEXT.md
docs/adr/0004-cross-platform-architecture.md
```

No registrar rutas de usuario, letras de unidad, `file://`, ubicaciones
temporales ni rutas absolutas de un worktree. Los enlaces externos conservan
su URL completa.

Después de mover un documento:

1. buscar su ruta anterior en todos los Markdown;
2. actualizar ADRs, contexto, queries y planes;
3. comprobar que la ruta nueva existe;
4. ejecutar `git diff --check`.

## Estilo

- Comentarios técnicos y docstrings de código se escriben en inglés.
- Texto visible para usuarios pertenece a los catálogos de localización.
- La documentación puede usar español o inglés, pero debe mantener un idioma
  coherente dentro de cada documento.
- Explicar razones, invariantes, evidencia y límites; evitar narrar lo obvio.
- Usar términos del proyecto de forma consistente: `LightController`,
  `WizProtocol`, `LogicalEffectFrame`, `PhysicalMapper` y
  `DesktopCapabilities`.
- No presentar observaciones de ingeniería inversa como API oficial.

## Checklist de mantenimiento

Antes de cerrar una fase documental:

1. clasificar cada documento nuevo;
2. usar el nombre y estado permitidos;
3. actualizar `PROJECT_CONTEXT.md` sólo con estado vigente;
4. enlazar el ADR relacionado cuando exista;
5. mover evidencia externa a `third-party/`;
6. archivar, no borrar, material reemplazado;
7. buscar rutas absolutas y referencias antiguas;
8. ejecutar `git diff --check`, `git status` y `git diff --stat`;
9. esperar revisión humana antes de commit, merge o push cuando el alcance lo
   indique.
