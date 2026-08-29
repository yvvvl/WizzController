# ADR 0005: migrar la interfaz a PySide6 + Qt Quick/QML

Fecha: 2026-08-29

Estado: aceptado para prototipo de paridad; migración productiva condicionada a
validación en Windows y Linux.

## Contexto

Flet permitió entregar WizZ Desktop v1.2.0 y validar control LAN, tray,
persistencia, targeting y builds en Windows/Linux. Sin embargo, la siguiente
etapa requiere una interfaz con:

- temas configurables y tema del sistema;
- transiciones y respuesta visual predecibles;
- layouts desktop compactos y fluidos;
- un selector de color WiZ de alta fidelidad;
- control preciso de foco, pointer input y refresco por componente;
- menos dependencia de widgets Flet deprecados.

Una reescritura en C++ o una migración a React/Tauri obligaría a sustituir o
duplicar el núcleo Python estable. Eso aumenta demasiado el riesgo de una
regresión en LAN, persistencia, hotkeys, tray y packaging.

## Decisión

La nueva interfaz se desarrollará con **PySide6 + Qt Quick/QML**.

- Python conserva `core/`, configuración, localización, actualizador
  read-only, plataforma y pruebas de lógica.
- QML pasa a ser la superficie declarativa, animada y responsive de escritorio.
- PySide6 expone un adaptador de aplicación con señales, slots y modelos para
  enlazar QML al núcleo Python.
- Flet continúa siendo el frontend de la versión pública v1.2.0 durante la
  transición; no se eliminará hasta lograr paridad verificada.
- La primera entrega Qt es un prototipo aislado, sin cambiar el protocolo WiZ
  ni los formatos de configuración.

Qt Quick Controls admite estilos y temas multiplataforma; Qt también ofrece
una bandeja de sistema para Windows y escritorios Linux compatibles. La
licencia, atribuciones y contenido de los paquetes se revisarán antes de la
distribución pública.

## Temas

El adaptador de preferencias persistirá una elección explícita:

- `system`: adopta claro/oscuro del sistema cuando esté disponible;
- `dark`: modo oscuro neutro de escritorio;
- `light`: modo claro de alto contraste;
- `midnight`: identidad azul profunda de WizZ Desktop.

Cada tema define tokens semánticos, no colores inline: fondo, superficie,
superficie elevada, texto, texto secundario, borde, foco, selección, éxito,
advertencia, error y controles deshabilitados. El selector WiZ usa su propia
paleta cromática, pero conserva contraste y focus ring del tema activo.

## Selector WiZ: referencia obligatoria

La interacción se replica de la aplicación WiZ actual sin copiar capturas,
activos ni marca visual de terceros:

1. área RGB continua que responde al arrastre;
2. acceso inmediato a blanco cálido y frío en la parte superior del área de
   color;
3. acceso a valor HEX y CCT/Kelvin;
4. muestras recientes/favoritas de acceso rápido;
5. brillo independiente;
6. aplicación inmediata o manual según la preferencia de WizZ Desktop;
7. resumen inequívoco del conjunto de luces al que se aplicará el cambio.

La referencia se basa en la documentación oficial de WiZ, que indica el
arrastre sobre la paleta RGB, y en la nota de versión 1.30.4 de WiZ Connected,
que añade acceso a blanco frío y cálido en la parte superior del área de color.
El diseño final mantiene las funciones propias de WizZ Desktop —operación LAN,
multi-selección y datos locales— y no pretende ser una copia de la app móvil.

## Prueba de concepto obligatoria

Antes de iniciar la migración completa, crear `qt_ui/` con:

- `main.py` de bootstrap PySide6;
- `Main.qml` y componentes QML para shell, temas y navegación;
- un modelo Python de luces virtuales;
- Home regular y compacto con selección inmediata de una/varias/todas;
- `WizColorPicker.qml` con RGB, cálido/frío, Kelvin, HEX, brillo y swatches;
- adaptador de comandos falso que registre acciones sin enviar tráfico LAN;
- pruebas de import, señal y modelo; capturas de Windows y Ubuntu.

La POC pasa solo si abre en ambos sistemas, alterna temas sin reiniciar,
selecciona luces al primer clic, conserva un frame fluido en drag y no aumenta
el consumo idle respecto a una línea base medida.

## Consecuencias

Positivas:

- UI de mayor fidelidad y control visual;
- temas con tokens compartidos;
- un camino viable para picker, animación y foco precisos;
- se conserva la inversión existente en Python;
- tray y packaging pueden migrar a APIs Qt en vez de soluciones auxiliares.

Costos y riesgos:

- coexistirán dos frontends temporalmente;
- se deben aprender QML, señales y ciclo de vida Qt;
- la POC debe validar tray, hotkeys, build y Linux antes de retirar Flet;
- cada migración de pantalla requiere paridad funcional y visual.

## Plan de retirada de Flet

1. POC Qt sin LAN real.
2. Bridge Qt → `LightController` con pruebas de targeting y comandos.
3. Paridad de Home + Color Studio con luces virtuales y una luz real.
4. Tray, instancia única, actualizaciones, ajustes, i18n y persistence.
5. Paridad de escenas, favoritos, rutinas y hotkeys.
6. Builds Windows/Linux, migración de configuración y beta cerrada.
7. Solo entonces cambiar el entry point público y archivar la interfaz Flet.
