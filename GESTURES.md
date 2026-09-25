# Gestos y funciones

Esta lista describe los gestos disponibles en `uv run asistente-jarvis control`.
El control comienza pausado; `F8` lo activa o pausa. `Esc` cierra el programa.
`uv run asistente-jarvis preview` muestra los gestos sin enviar entradas al sistema.

## Una mano

| Gesto | Función | Estado |
|---|---|---|
| Índice extendido | Mover el cursor de forma relativa | Disponible |
| Puño cerrado | Recolocar la mano sin mover el cursor; vuelve a señalar para seguir | Disponible |
| Pinza breve | Clic izquierdo al soltar, sin desplazar el cursor | Disponible |
| Pinza sostenida al menos 0,45 s | Arrastrar; soltar la pinza termina el arrastre | Disponible |
| Cuatro dedos largos extendidos, juntos o separados | STOP: libera el mouse y pausa el control | Disponible |
| C sostenida al menos 0,45 s | Copiar (`Ctrl+C`) | Disponible |
| V hacia arriba sostenida al menos 0,45 s | Pegar (`Ctrl+V`) | Disponible |
| V invertida, dedos hacia abajo, sostenida al menos 0,45 s | Seleccionar todo | Disponible |
| Pulgar arriba | Reservado para dictado | Solo detección |
| Pulgar, índice y meñique extendidos (`ILoveYou`) durante 0,45 s | Abrir recorte de pantalla (`Win+Shift+S`) | Disponible |

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
| Un puño + índice de la otra mano hacia arriba/abajo | Desplazamiento vertical | Disponible |
| Un puño + índice de la otra mano hacia izquierda/derecha | Desplazamiento horizontal | Disponible |
| Un puño + V de la otra mano durante 0,35 s | Mantener `Alt` y abrir el selector con `Tab` | Disponible |
| En el selector, inclinar la muñeca con la V hacia la derecha/izquierda | Ventana siguiente/anterior; sostener la inclinación repite pasos | Disponible |
| Un puño + pulgar lateral de la otra mano hacia la izquierda durante 0,45 s | Deshacer (`Ctrl+Z`) | Disponible |
| Un puño + pulgar lateral de la otra mano hacia la derecha durante 0,45 s | Rehacer (`Ctrl+Y`) | Disponible |
| STOP con cualquiera de las dos manos | Pausar todo y liberar el mouse | Disponible |

Al aparecer dos manos, se cancelan el clic o arrastre pendiente y los atajos de
una mano. Mantén ambas pinzas unos 0,35 s para establecer la distancia inicial;
luego mueve las manos. Cada cambio suficiente de distancia envía un paso de
zoom. Al desaparecer una mano, la pinza restante no inicia un clic hasta que
se suelte. El efecto de zoom depende de que la aplicación activa admita estos
atajos.

Para desplazar, mantén un puño fijo y señala con la otra mano. La primera
dirección predominante fija el eje del desplazamiento. Para cambiar de eje,
deja de señalar y vuelve a señalar. La rueda actúa sobre la ventana bajo el
cursor; algunas aplicaciones no admiten desplazamiento horizontal.

Para cambiar aplicaciones, mantén un puño fijo y forma una V con la otra mano
durante 0,35 s. Se mantiene `Alt` y se pulsa `Tab` una vez para abrir el
selector. Inclina la muñeca con la V unos 25° hacia la derecha para avanzar o
hacia la izquierda para retroceder. Si mantienes la inclinación, se repite un
paso aproximadamente cada 0,32 s y puedes recorrer muchas ventanas sin
desplazar el brazo. Devuelve la V a su orientación inicial para detener los
pasos. Suelta el puño, haz STOP, pausa con `F8` o retira una mano para soltar
`Alt` y escoger la ventana visible. La inclinación se mide en el plano de la
cámara; no hace falta girar la palma para mostrar su dorso.

Para deshacer o rehacer, mantén un puño y extiende el pulgar de la otra mano
hacia un lado durante 0,45 s. El atajo se envía una vez por postura; vuelve a
una posición neutra y repite el pulgar para otra acción. La dirección sigue
la imagen reflejada que muestra la cámara de forma predeterminada.

Los atajos puntuales como copiar, pegar, deshacer, rehacer, seleccionar todo y
recortar pantalla muestran un aviso pequeño sobre el escritorio durante 1,6 s.
El aviso no cambia el foco de la aplicación ni bloquea clics.

## Gestos que MediaPipe ofrece por separado

Este proyecto usa **Hand Landmarker** para obtener 21 puntos por mano y
clasifica los gestos anteriores con geometría propia. MediaPipe tiene además
otra tarea, **Gesture Recognizer**, cuyo modelo estándar reconoce estas
categorías:

| Categoría estándar | Significado aproximado |
|---|---|
| `None` | Ningún gesto reconocido |
| `Closed_Fist` | Puño cerrado |
| `Open_Palm` | Palma abierta |
| `Pointing_Up` | Índice apuntando arriba |
| `Thumb_Down` | Pulgar abajo |
| `Thumb_Up` | Pulgar arriba |
| `Victory` | V con índice y medio |
| `ILoveYou` | Pulgar, índice y meñique extendidos |

Estas categorías estándar **no se usan todavía** para decidir acciones en el
programa. La pinza, C y V invertida son gestos personalizados de este
proyecto; no aparecen en esa lista estándar. Si más adelante cambiamos al
modelo Gesture Recognizer, podremos combinar sus etiquetas con los gestos
geométricos personalizados.

## Ideas para siguientes tandas

| Gesto propuesto | Posible función | Consideración |
|---|---|---|
| Pulgar arriba sostenido | Iniciar dictado | Requiere grabación, transcripción y una señal de fin clara |
| `Thumb_Down` sostenido | Deshacer (`Ctrl+Z`) | Requiere agregar o entrenar un detector sin chocar con pulgar arriba |
| Dos manos girando en sentidos opuestos | Rotar lienzo o imagen | Depende de atajos de cada aplicación |

Estas ideas todavía no envían comandos. Antes de agregarlas conviene comprobar
que sus posturas no se confundan con STOP, pinza, C, V o A.

## Referencias de atajos

- [Windows: métodos abreviados de teclado](https://support.microsoft.com/es-es/accessibility/windows/keyboard-shortcuts-in-windows)
- [Word: seleccionar texto](https://support.microsoft.com/es-es/word/select-text)
- [Excel: métodos abreviados de teclado](https://support.microsoft.com/es-es/accessibility/excel/keyboard-shortcuts-in-excel)
- [MediaPipe: Gesture Recognizer y categorías estándar](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/GestureRecognizerOptions)
