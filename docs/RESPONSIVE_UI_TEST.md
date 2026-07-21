# Prueba manual de UI responsive y Color Studio

Esta versión no cambia el ciclo de vida de ventana/bandeja ni la lógica WiZ. La prueba se concentra en el layout y en el seguimiento del puntero del picker.

## 1. Color Studio: bordes y esquinas

1. Abre **Color** y activa o desactiva **Aplicar en vivo** según prefieras.
2. Arrastra lentamente el círculo a las cuatro esquinas del cuadro HSV.
3. Repite con movimientos rápidos y llegando exactamente al borde.
4. Verifica:
   - superior izquierda: `S 0% · V 100%`;
   - superior derecha: `S 100% · V 100%`;
   - inferior izquierda: `S 0% · V 0%`;
   - inferior derecha: `S 100% · V 0%`;
   - el círculo nunca salta al borde opuesto;
   - no es necesario sacar el mouse del picker.
5. Lleva la barra de matiz a ambos extremos y confirma que el indicador tampoco salta.

El thumb permanece completamente dentro del control. Por eso su centro queda unos píxeles hacia dentro cuando el puntero está exactamente sobre el borde exterior; el valor sí debe alcanzar 0% o 100%.

## 2. Resize mínimo y normal

Prueba estos tamaños aproximados:

- `720 × 540` (mínimo soportado);
- `820 × 600`;
- `1080 × 720`;
- maximizada.

En cada tamaño recorre **Inicio, Color, Escenas, Favs, Rutinas, Ajustes y Hotkeys**. Confirma que:

- no aparece overflow horizontal;
- los botones no salen de las cards;
- textos largos usan salto de línea o elipsis;
- formularios y acciones bajan a una nueva fila cuando falta ancho;
- el contenido vertical sigue accesible mediante scroll;
- el NavigationRail reduce sus etiquetas al estrechar la ventana;
- el picker cambia de tamaño sin deformarse ni perder sus extremos.

## 3. Pantallas que antes se cortaban

### Ajustes

- Los cuatro bloques de destino se distribuyen en una o varias filas.
- Las opciones de bandeja se convierten en cards independientes.
- Las acciones de cada ampolleta permanecen dentro de su tarjeta.

### Hotkeys

- Estado, slider de antirebote y botón **Re-registrar** permanecen visibles.
- Categoría, búsqueda, acción, combinación y botones se reordenan sin corte lateral.
- Las filas de hotkeys guardadas se compactan cuando falta ancho.

### Color

- Blancos Kelvin, armonías, colores rápidos y moods no comprimen sus textos hasta volverlos ilegibles.
- HEX/R/G/B se reorganizan en la ventana estrecha.
- El botón redundante **Rojo puro** ya no existe.

## 4. Regresión funcional

Después del resize, valida también:

- una hotkey con la ventana visible, minimizada y oculta en bandeja;
- abrir el menú de bandeja y ejecutar una acción;
- cambiar color, brillo, blanco y escena;
- ejecutar un favorito y una rutina.

Así se confirma que el refactor visual no alteró `ActionSequenceExecutor`, el servicio global de hotkeys ni el control UDP WiZ.
