# Third-party review: WizScreenSyncController

Status: Investigation

- **Fecha de auditoría:** 2026-07-26
- **Proyecto evaluado:** WizScreenSyncController
- **Repositorio original:** https://github.com/TechAntohere/WizScreenSyncController
- **Autor/propietario reportado:** TechAntohere
- **Revisión auditada:** `0feb5749a28389bc6971639467f6cb7fd464ebe2`
- **Último cambio de esa revisión:** 2026-02-07, `improved latency and Ui`

## Alcance verificado

La rama `main` auditada contiene solamente:

- `README.md`;
- `requirements.txt`;
- `wizscreensynccontroller.py`.

El archivo principal tiene 1.796 líneas y reúne UI PyQt6, captura de pantalla,
análisis de color, mapeo de zonas, descubrimiento WiZ, persistencia, bandeja y
envío UDP. No se encontraron pruebas, configuración de CI, metadatos de
paquete ni separación entre motor y transporte.

Fuentes congeladas:

- [repositorio](https://github.com/TechAntohere/WizScreenSyncController);
- [script auditado](https://github.com/TechAntohere/WizScreenSyncController/blob/0feb5749a28389bc6971639467f6cb7fd464ebe2/wizscreensynccontroller.py);
- [dependencias](https://github.com/TechAntohere/WizScreenSyncController/blob/0feb5749a28389bc6971639467f6cb7fd464ebe2/requirements.txt);
- [commit auditado](https://github.com/TechAntohere/WizScreenSyncController/commit/0feb5749a28389bc6971639467f6cb7fd464ebe2).

## Licencia encontrada

**No se encontró una licencia de proyecto.**

Se comprobaron y no existen en la revisión auditada:

- `LICENSE`;
- `LICENSE.md`;
- `LICENSE.txt`;
- `COPYING`;
- `COPYING.txt`;
- `pyproject.toml`;
- `setup.py`.

El `README.md` tampoco declara licencia. Que el repositorio sea público no
concede por sí solo permiso para reproducir, modificar o distribuir el código.
GitHub explica que, sin licencia, se aplican los derechos de autor por defecto:

https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

Esta revisión no constituye asesoría legal.

## Permiso comunicado

El brief de esta auditoría declara que el autor autorizó integrar la lógica en
WizZ Desktop siempre que se otorguen los créditos correspondientes.

Ese permiso se registra aquí como **permiso reportado por el mantenedor de
WizZ**, no como una licencia verificable presente en el repositorio. Antes de
copiar o adaptar expresión concreta del código debe conservarse una evidencia
escrita del mensaje original y confirmar con TechAntohere:

1. que controla los derechos de todo el código de la revisión indicada;
2. que autoriza expresamente usar, copiar, modificar y distribuir el código,
   tanto en fuente como en binarios de WizZ Desktop;
3. si el permiso es mundial, gratuito, no exclusivo y permanente;
4. si permite redistribuir modificaciones bajo los términos elegidos para
   WizZ Desktop;
5. el texto exacto de atribución y dónde debe mostrarse;
6. si el permiso cubre revisiones futuras o sólo el commit auditado;
7. si existen contribuciones, recursos o fragmentos de terceros no declarados.

Hasta resolver esos puntos, la autorización no debe interpretarse como una
licencia open source ni como permiso inequívoco para copiar el archivo
principal.

## Actualización técnica RGBIC

TechAntohere aportó información conceptual adicional después de la auditoría:

- `sceneId: 257` funcionó inicialmente como contenedor observado;
- después de una actualización de firmware, 257 pareció quedar sobrescrito por
  un efecto guardado en el dispositivo;
- cambiar a `sceneId: 258` recuperó el comportamiento esperado;
- los slots pueden depender del firmware y del estado interno, por lo que
  ninguno debe considerarse una constante;
- los datos dinámicos se ubican en `elm`;
- `elm.steps` se procesa secuencialmente;
- `width` representa un span absoluto de segmentos físicos, no una proporción
  relativa;
- cada step contiene un `modifier`; 100 se observó como color estático,
  101–125 parecen efectos internos y otros rangos siguen sin documentar;
- el número de steps no identifica la longitud física instalada;
- una tira cortada puede conservar el mismo modelo reportado;
- un envío exitoso no prueba que el efecto haya sido aplicado.

Esta corrección fundamenta la separación entre zonas lógicas, mapping físico
y steps RGBIC descrita en `docs/adr/0003-effects-engine-architecture.md`. No se
copió código de WizScreenSyncController ni se adoptaron sus constantes como
implementación productiva. Una implementación futura necesita capabilities,
firmware awareness, probing, fallback acotado de contenedores y validación del
comportamiento aplicado. No debe crear tablas `firmware -> sceneId`, hardcodear
257/258 ni decidir sólo por versión de firmware.

Los aportes conceptuales atribuidos a TechAntohere abarcan
WizScreenSyncController, `elm.steps`, `width` físico, `modifier`, slots
`sceneId` variables y comportamiento dependiente de firmware.

La actualización técnica no cambia el estado legal de la auditoría. El
permiso/licencia, su alcance y el texto definitivo de créditos continúan
pendientes de formalización.

## Compatibilidad con WizZ Desktop

No puede emitirse una conclusión definitiva de compatibilidad de licencias:

- WizScreenSyncController no declara licencia;
- WizZ Desktop tampoco contiene una licencia raíz en la revisión local
  auditada;
- el permiso privado no define todavía derechos de redistribución;
- las dependencias mantienen sus propias obligaciones.

La dependencia más problemática del proyecto externo es `PyQt6`. La edición
publicada en PyPI está bajo GPLv3, o requiere una licencia comercial cuando la
aplicación no sea compatible con GPL. Riverbank no ofrece PyQt bajo LGPL:

https://www.riverbankcomputing.com/software/pyqt

WizZ no necesita adoptar PyQt6 para incorporar Screen Sync. La UI externa debe
quedar fuera de cualquier integración. Si en el futuro se decide migrar la UI
a Qt, PySide6 debe evaluarse por separado bajo sus términos LGPL/GPL/comerciales.

## Dependencias y obligaciones independientes

| Dependencia externa | Estado en el proyecto | Licencia observada | Evaluación para WizZ |
| --- | --- | --- | --- |
| PyQt6 | requerida, sin pin | GPL-3.0-only o comercial | No incorporar con Screen Sync; riesgo alto y runtime grande |
| mss | requerida, sin pin | MIT | Candidata como backend Windows/X11 tras pin y pruebas |
| NumPy | requerida, sin pin | BSD y avisos de componentes | Candidata para análisis vectorizado; requiere pin compatible con Python 3.11 |
| dxcam | import opcional, pero ausente de `requirements.txt` | MIT | Candidata opcional sólo para Windows; declarar y fijar versión si se adopta |

Las obligaciones de esas librerías no quedan cubiertas por el permiso de
TechAntohere. Deben auditarse y distribuirse sus avisos por separado si se
incorporan.

## Condiciones para reutilización

### Permitido en esta fase

- estudiar la arquitectura y el comportamiento observable;
- describir conceptos técnicos;
- proponer una arquitectura propia;
- crear pruebas y una implementación independiente una vez aprobada la fase;
- citar el repositorio y reconocer la inspiración.

Como referencia estadounidense, las ideas, métodos y sistemas no reciben la
misma protección que su expresión concreta. La jurisdicción aplicable debe
confirmarse; en cualquier caso, una reimplementación debe evitar copiar
estructura, nombres, comentarios o bloques del script. Referencia:

https://www.copyright.gov/circs/circ33.pdf

### Bloqueado hasta confirmar la licencia

- copiar funciones o fragmentos;
- trasladar el monolito a módulos;
- copiar el formato RGBIC con sus constantes como implementación productiva;
- distribuir código derivado del archivo principal;
- afirmar que el proyecto externo es MIT, GPL u open source;
- publicar créditos definitivos que presenten una licencia todavía inexistente.

## Propuesta de créditos

La siguiente entrada es un **borrador interno**. No debe publicarse como aviso
definitivo. `THIRD_PARTY_NOTICES.md` sólo puede conservar una nota interna no
distribuible hasta formalizar permiso/licencia.

```markdown
## WizScreenSyncController

Screen Sync in WizZ Desktop is based in part on concepts from
WizScreenSyncController.

Author: TechAntohere
Repository: https://github.com/TechAntohere/WizScreenSyncController
Audited revision: 0feb5749a28389bc6971639467f6cb7fd464ebe2
Permission/license: TO BE CONFIRMED
```

Si finalmente se copia o modifica código, `based in part on concepts` puede no
ser suficiente. El texto deberá reflejar el alcance real, incorporar la
licencia o permiso acordado y enlazar o incluir sus términos completos.

## Decisión de esta auditoría

**No integrar código en el estado legal actual.** La ruta recomendada es
preservar la atribución, obtener una licencia o permiso escrito inequívoco y
desarrollar una implementación modular propia detrás de `LightController`.
