# ADR 0007: reabrir la evaluación de Qt Quick con fidelidad comprobable

- Status: Draft
- Date: 2026-08-31
- Scope: frontend desktop y frontera QML/Python

## Contexto

El primer POC Qt documentado en ADR 0005 fue rechazado porque utilizó controles
visualmente genéricos y no demostró que pudiera reproducir la interfaz Flet
aprobada. La interfaz Flet posterior sí fijó el lenguaje visual del producto,
pero conserva límites de frame pacing, pointer input, ventanas auxiliares y
control de composición que afectan especialmente al selector de color y al
Quick Panel.

El núcleo Python, el protocolo LAN, targeting, configuración, escenas,
favoritos, rutinas, hotkeys y pruebas existentes siguen siendo inversión
válida. Una reescritura simultánea del frontend y del núcleo aumentaría el
riesgo sin aportar valor al usuario.

## Decisión propuesta

Reabrir Qt Quick como una migración progresiva y comprobable, no como una
reescritura inmediata.

- Python continúa siendo dueño de `core/`, persistencia, plataforma y lógica.
- PySide6 expone modelos, propiedades, señales y comandos pequeños a QML.
- QML dibuja controles propios; no se aceptan estilos Qt predeterminados como
  representación final del producto.
- Flet permanece ejecutable y distribuible hasta que exista paridad completa.
- El Quick Panel es una segunda ventana Qt que comparte el mismo controlador.
- La lógica WiZ nunca se duplica dentro de QML.

La rama de evaluación es `codex/qtquick-desktop-shell`, basada en
`feature/v1.3.0-ui-foundation`. RGBIC continúa fuera de este corte estable.

## Evidencia inicial

El primer corte vertical implementa, sin tráfico WiZ:

- shell desktop sin marco del sistema;
- Home con tres ampolletas virtuales, selección, encendido, brillo y acciones;
- ripple expansivo personalizado de 420 ms;
- Quick Panel de 392 × 548 como ventana nativa independiente;
- un solo `VirtualLightController` compartido por bridge y vistas;
- capturas automáticas para revisión visual;
- pruebas del modelo y comandos del bridge.

Esta evidencia demuestra viabilidad visual y arquitectónica, pero no acepta
todavía la sustitución de Flet.

## Condiciones para aceptar la migración

1. Home y Color Studio alcanzan paridad funcional y visual.
2. El color picker sigue el cursor a la frecuencia de composición de la
   pantalla y separa el frame visual del throttle LAN.
3. Los temas cambian en caliente y reduced motion afecta todas las primitivas.
4. Quick Panel, tray, hotkeys e instancia única funcionan en Windows.
5. Se validan build, inicio, configuración y tray en Linux.
6. Escenas, favoritos, rutinas y ajustes conservan formatos y comportamiento.
7. El consumo idle y el tamaño distribuido se miden contra la versión Flet.
8. La suite completa y una matriz manual de hardware pasan antes del cambio de
   entry point.

## Consecuencias

Durante la evaluación coexistirán dos frontends. Esto aumenta temporalmente el
código visual, pero mantiene recuperable cada paso y permite rechazar Qt sin
afectar el release público. PySide6 se mantiene como extra opcional hasta que
la decisión cambie a Accepted.

