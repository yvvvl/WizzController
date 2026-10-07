# Color reactivo del logo

El icono de WizZ en la barra lateral y el icono pequeño de la barra superior
comparten un único color. Cuando hay **una sola ampolleta configurada,
encendida y conectada**, toman el color mostrado por ella; cuando hay dos o
más, o la única está apagada/desconectada, usan el color de acento del tema.
La opción **acento de marca dinámico** de Ajustes puede desactivar la reacción
de la luz y dejar siempre el color del tema.

No alternamos entre ampolletas cuando hay varias: esa animación no indicaba
claramente cuál luz representaba el logo. Con una sola, los cambios RGB que el
controlador LAN entrega actualizan el logo con una transición breve; el modo
virtual también usa sus fotogramas de escenas animadas. El icono no modifica
la luz ni envía comandos adicionales.

Para escenas dinámicas de una ampolleta real hay un límite importante: WizZ
solo puede mostrar el color instantáneo si la ampolleta lo informa por LAN.
Cuando solo informa el identificador de la escena, el logo usa un color
representativo de esa escena; no simulamos una sincronización exacta que no
podemos verificar. Si se selecciona «reducir movimiento», la transición del
logo se desactiva.

Prueba sin hardware: ejecuta con `WIZZ_DEV_VIRTUAL_BULBS=1`, cambia el color
o activa una escena dinámica y mira el icono. Repite con
`WIZZ_DEV_VIRTUAL_BULBS=3`: debe quedarse con el acento del tema. En ambos
casos las ampolletas virtuales no envían tráfico WiZ.
