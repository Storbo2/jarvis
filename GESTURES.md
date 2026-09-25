# Gestos y funciones

Esta lista describe los gestos disponibles en `uv run asistente-jarvis control`.
El control comienza pausado; `F8` lo activa o pausa. `Esc` cierra el programa.
`uv run asistente-jarvis preview` muestra los gestos sin enviar entradas al sistema.

## Una mano

| Gesto | Función | Estado |
|---|---|---|
| Índice extendido | Mover el cursor de forma relativa | Disponible |
| Mano neutra, sin señalar | Recolocar la mano sin mover el cursor | Disponible |
| Pinza breve | Clic izquierdo al soltar, sin desplazar el cursor | Disponible |
| Pinza sostenida al menos 0,45 s | Arrastrar; soltar la pinza termina el arrastre | Disponible |
| Cuatro dedos largos extendidos, juntos o separados | STOP: libera el mouse y pausa el control | Disponible |
| C sostenida al menos 0,45 s | Copiar (`Ctrl+C`) | Disponible |
| V hacia arriba sostenida al menos 0,45 s | Pegar (`Ctrl+V`) | Disponible |
| V invertida, dedos hacia abajo, sostenida al menos 0,45 s | Seleccionar todo | Disponible |
| Pulgar arriba | Reservado para dictado | Solo detección |

El gesto de seleccionar todo usa `Ctrl+E` en el Explorador de archivos y en
Word, Excel y PowerPoint de escritorio; usa `Ctrl+A` en las demás aplicaciones.
Esta elección se basa en el programa de la ventana activa, no en el
idioma del teclado. Si una aplicación usa otro atajo, ejecuta `control` con
`--select-all-mode ctrl-a` o `--select-all-mode ctrl-e`.

## Dos manos

| Gesto | Función | Estado |
|---|---|---|
| Una pinza con cada mano; separar las manos | Zoom + (`Ctrl` y suma del teclado numérico) | Disponible |
| Una pinza con cada mano; acercar las manos | Zoom − (`Ctrl` y resta del teclado numérico) | Disponible |
| STOP con cualquiera de las dos manos | Pausar todo y liberar el mouse | Disponible |

Al aparecer dos manos, se cancelan el clic o arrastre pendiente y los atajos de
una mano. Mantén ambas pinzas unos 0,35 s para establecer la distancia inicial;
luego mueve las manos. Cada cambio suficiente de distancia envía un paso de
zoom. Al desaparecer una mano, la pinza restante no inicia un clic hasta que
se suelte. El efecto de zoom depende de que la aplicación activa admita estos
atajos.

## Ideas para siguientes tandas

| Gesto propuesto | Posible función | Consideración |
|---|---|---|
| Pulgar arriba sostenido | Iniciar dictado | Requiere grabación, transcripción y una señal de fin clara |
| Dos dedos de una mano movidos verticalmente | Desplazamiento de página | Reservar una postura distinta de la V de pegar |
| Dos manos girando en sentidos opuestos | Rotar lienzo o imagen | Depende de atajos de cada aplicación |
| Puño cerrado sostenido | Pausa temporal del cursor | Debe convivir con la recolocación actual |

Estas ideas todavía no envían comandos. Antes de agregarlas conviene comprobar
que sus posturas no se confundan con STOP, pinza, C, V o A.

## Referencias de atajos

- [Windows: métodos abreviados de teclado](https://support.microsoft.com/es-es/accessibility/windows/keyboard-shortcuts-in-windows)
- [Word: seleccionar texto](https://support.microsoft.com/es-es/word/select-text)
- [Excel: métodos abreviados de teclado](https://support.microsoft.com/es-es/accessibility/excel/keyboard-shortcuts-in-excel)
