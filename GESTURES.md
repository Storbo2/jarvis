# Gestos y funciones

Esta lista describe los gestos disponibles en `uv run asistente-jarvis control`.
El control comienza pausado; `F8` lo activa o pausa. `Ctrl+Q` cierra el programa.
`F9` abre la calibración del cursor y guarda los ajustes al cerrarla; `F10`
alterna el diagnóstico visual de puntos bruto/filtrado y posición del cursor.
`uv run asistente-jarvis preview` muestra los gestos sin enviar entradas al sistema.
Para ajustar el proyecto en otro equipo o con varios monitores, sigue
[CALIBRATION.md](CALIBRATION.md).

## Una mano

| Gesto | Función | Estado |
|---|---|---|
| Índice extendido | Mover el cursor de forma relativa | Disponible |
| Puño con los nudillos apuntando a la cámara | Recolocar la mano sin mover el cursor; vuelve a señalar para seguir | Disponible |
| Mano cerrada normal | Deja el cursor quieto; sirve como modificador de dos manos | Disponible |
| Pinza breve | Clic izquierdo al soltar, sin desplazar el cursor | Disponible |
| Pinza sostenida al menos 0,45 s | Arrastrar; soltar la pinza termina el arrastre | Disponible |
| Dos pinzas breves seguidas sobre el mismo punto | Doble clic izquierdo | Disponible |
| Pulgar y dedo medio levantado juntos durante 0,32 s, con índice extendido | Clic derecho en la posición actual | Disponible |
| Palma abierta con una sola mano | Pose disponible para combinaciones; no pausa el control | Disponible |
| C sostenida al menos 0,45 s | Copiar (`Ctrl+C`) | Disponible |
| V hacia arriba con pulgar plegado, sostenida al menos 0,45 s | Pegar (`Ctrl+V`) | Disponible |
| V invertida, dedos hacia abajo, sostenida al menos 0,45 s | Seleccionar todo | Disponible |
| Pulgar arriba sostenido 0,6 s | Iniciar dictado progresivo con Whisper large-v3 | Disponible |
| Pulgar abajo sostenido 0,6 s | Terminar dictado y procesar el audio pendiente | Disponible |
| Pulgar, índice y meñique extendidos (`ILoveYou`) durante 0,45 s | Abrir recorte de pantalla (`Win+Shift+S`) | Disponible |
| Garra con una sola mano visible: dedos plegados y puntas hacia la cámara, sostenida 0,52 s | Tomar y arrastrar la ventana activa por su barra de título | Disponible |
| Abrir la mano que sostiene una ventana | Soltar y maximizar la ventana | Disponible |
| Pasar de la garra al índice levantado | Soltar la ventana y continuar con el cursor | Disponible |

El gesto de seleccionar todo usa `Ctrl+E` en el Explorador de archivos y en
Word, Excel y PowerPoint de escritorio; usa `Ctrl+A` en las demás aplicaciones.
Esta elección se basa en el programa de la ventana activa, no en el
idioma del teclado. Si una aplicación usa otro atajo, ejecuta `control` con
`--select-all-mode ctrl-a` o `--select-all-mode ctrl-e`.

Para recolocar, orienta los nudillos hacia la cámara como si fueras a golpear
la pantalla. La etiqueta debe decir `PUNO FRONTAL / RECOLOCAR`. Una mano
simplemente cerrada se muestra como `MANO CERRADA`: también deja quieto el
cursor, pero no interrumpe la detección de una pinza que se está formando.
Una fluctuación breve de la distancia entre pulgar e índice tampoco corta un
arrastre; abrir la pinza lo termina.

## Dos manos

| Gesto | Función | Estado |
|---|---|---|
| Una pinza con cada mano; separar las manos | Zoom + (`Ctrl` y suma del teclado numérico) | Disponible |
| Una pinza con cada mano; acercar las manos | Zoom − (`Ctrl` y resta del teclado numérico) | Disponible |
| Un puño + índice de la otra mano hacia arriba/abajo | Desplazamiento vertical | Disponible |
| Un puño + índice de la otra mano hacia izquierda/derecha | Desplazamiento horizontal | Disponible |
| Un puño + V de la otra mano durante 0,28 s | Mantener `Alt` y abrir el selector con `Tab` | Disponible |
| En el selector, inclinar la muñeca con la V hacia la derecha/izquierda | Ventana siguiente/anterior; sostener la inclinación repite pasos | Disponible |
| Un puño + pulgar lateral de la otra mano hacia la izquierda durante 0,45 s | Deshacer (`Ctrl+Z`) | Disponible |
| Un puño + pulgar lateral de la otra mano hacia la derecha durante 0,45 s | Rehacer (`Ctrl+Y`) | Disponible |
| Un puño + pulgar arriba/abajo | Subir/bajar volumen; mantenerlo repite | Disponible |
| Un puño + palma abierta durante 0,38 s | Reproducir/pausar multimedia | Disponible |
| Un puño + cuernos (índice y meñique) con inclinación leve a la izquierda/derecha | Pista anterior/siguiente | Disponible |
| Mientras tomas una ventana, la otra mano señala a la izquierda/derecha | Encajar en la mitad indicada | Disponible |
| Con dos o más monitores, llevar la garra con decisión al borde izquierdo/derecho | Enviar la ventana al monitor adyacente | Disponible |
| Dos palmas abiertas simultáneas durante 2 s | STOP: pausar todo y liberar el mouse | Disponible |

Al aparecer dos manos, se cancelan el clic o arrastre pendiente y los atajos de
una mano. Mantén ambas pinzas unos 0,35 s para establecer la distancia inicial;
luego mueve las manos. Cada cambio suficiente de distancia envía un paso de
zoom. Al desaparecer una mano, la pinza restante no inicia un clic hasta que
se suelte. El efecto de zoom depende de que la aplicación activa admita estos
atajos. Una pérdida breve de la etiqueta de pinza no reinicia la calibración
del zoom.

Para desplazar, mantén un puño fijo y señala con la otra mano. El modificador
de dos manos admite tanto el puño normal como el frontal. La primera
dirección predominante fija el eje del desplazamiento. Para cambiar de eje,
deja de señalar y vuelve a señalar. La rueda actúa sobre la ventana bajo el
cursor; algunas aplicaciones no admiten desplazamiento horizontal.

Con dos manos visibles, el programa resuelve la postura como pareja: si una
mano se parece a una pinza y la otra señala, forma una V o muestra un pulgar
lateral, la primera aparece como `PUNO / MODIFICADOR`. Esto evita que un puño
confundido con pinza bloquee scroll, Alt+Tab o deshacer/rehacer. Dos manos
clasificadas como pinza siguen reservadas para el zoom. Con una sola mano,
la pinza conserva su prioridad para clic y arrastre.

Para cambiar aplicaciones, mantén un puño fijo y forma una V con la otra mano
durante 0,28 s. Se mantiene `Alt` y se pulsa `Tab` una vez para abrir el
selector. Inclina la mano en el plano de la cámara unos 10° hacia la derecha para avanzar o
hacia la izquierda para retroceder. El primer cruce del umbral avanza de
inmediato. Si mantienes la inclinación, los pasos se repiten más rápido cuanto
mayor sea el giro, desde aproximadamente 0,28 hasta 0,12 s, y puedes recorrer muchas ventanas sin
desplazar el brazo. Devuelve la V a su orientación inicial para detener los
pasos. Suelta el puño, haz STOP, pausa con `F8` o retira una mano para soltar
`Alt` y escoger la ventana visible. La cámara indica el giro medido y el umbral
de 10 grados. Puedes inclinar toda la mano y el antebrazo; girar la palma para
mostrar su dorso no produce este movimiento. Una vez abierto el selector, se
sigue el giro aunque el detector deje de mostrar la etiqueta `V` por un instante.

Para deshacer o rehacer, mantén un puño y extiende el pulgar de la otra mano
hacia un lado durante 0,45 s. El atajo se envía una vez por postura; vuelve a
una posición neutra y repite el pulgar para otra acción. La dirección sigue
la imagen reflejada que muestra la cámara de forma predeterminada.

Para los controles multimedia, usa una mano cerrada como modificador. Con el
pulgar de la otra mano hacia arriba o abajo subes o bajas el volumen; mantener
la pose repite pasos cada 0,22 s. Una palma abierta reproduce o pausa una vez por
postura. Los cuernos usan una inclinación lateral leve de la mano activa: desplázala
hacia la izquierda para la pista anterior o hacia la derecha para la siguiente.
La zona neutra de los cuernos se redujo para que no sea necesario inclinar
tanto la muñeca. Dos palmas abiertas quedan reservadas exclusivamente para STOP.

Para mover una ventana, deja en primer plano la ventana que quieres mover y
forma una garra con una sola mano visible durante 0,52 s. Si la ventana está maximizada se restaura antes
de iniciar el arrastre. Mantén la garra para moverla y abre esa mano para
maximizarla al soltar. Levanta solamente el índice para soltarla en su posición
y retomar el movimiento normal del cursor. Mientras la arrastras, señala con
la otra mano a la izquierda o derecha durante 0,35 s para encajarla a una mitad.
Lleva la garra rápidamente hacia abajo para minimizar la ventana y liberar el
cursor; se exige velocidad, recorrido y llegar a la zona inferior para no
confundirlo con un arrastre normal. La velocidad se calcula sobre varios
fotogramas, así que basta con un gesto descendente firme y continuo.
Con varios monitores, lleva la garra
desde el centro hasta un borde de la cámara para enviar la ventana al monitor
adyacente. Esta acción usa la barra de título de ventanas normales de Windows;
el modo pantalla completa propio de cada navegador, como F11, debe salir antes
con su propio atajo.

La toma de ventanas no comienza mientras hay dos manos visibles. En ese caso,
si el detector confunde el puño modificador con una garra, se interpreta como
puño para que volumen, reproducción, cambio de pista, scroll y Alt+Tab sigan
teniendo prioridad.

Los atajos puntuales como copiar, pegar, deshacer, rehacer, seleccionar todo y
recortar pantalla muestran un aviso pequeño sobre el escritorio durante 1,6 s.
El aviso no cambia el foco de la aplicación ni bloquea clics.

Durante el dictado, dos palmas sostenidas 2 s o `F8` cancelan la grabación. Deja enfocado el campo
de texto mientras aparecen los fragmentos transcritos. El audio se conserva
solo en memoria y la grabación se detiene automáticamente al cumplir 60 segundos.
Di «coma», «punto» o «dos puntos» para escribir `,`, `.` o `:`; los signos que
Whisper añada sin una orden se descartan. «Enter» inserta un salto de línea con
`Shift+Enter`. «Enviar» ejecuta `Enter` normal como orden aislada; espera a que
se escriba el fragmento anterior antes de decirlo. «Borrar palabra» quita la
última palabra con `Ctrl+Backspace` y «Borrar todo» limpia el campo con
`Ctrl+A` y `Backspace`; di esas órdenes solas.

Para recortar, forma `ILoveYou` hasta que aparezca la interfaz de Recortes.
Señala con el índice para colocar el cursor en una esquina de la zona deseada.
Forma una pinza y, sin soltarla, mueve la mano hasta la esquina opuesta; al
abrir la pinza se completa el recorte. En este modo la pinza inicia el arrastre
de inmediato, sin esperar los 0,45 s del arrastre normal. El modo caduca después
de 30 s o al hacer STOP o pulsar `F8`.

La cámara se muestra en un panel compacto siempre visible en la zona superior
derecha, separado de los bordes para dejar accesibles los botones y la barra de
desplazamiento de otras aplicaciones. La interfaz usa una cabecera oscura,
detalles cian, alertas naranjas y estados `ONLINE`/`STANDBY`. La ventana se puede
mover o redimensionar manualmente si necesitas otra ubicación.

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
| Dos manos girando en sentidos opuestos | Rotar lienzo o imagen | Depende de atajos de cada aplicación |

Estas ideas todavía no envían comandos. Antes de agregarlas conviene comprobar
que sus posturas no se confundan con STOP, pinza, C, V o A.

## Referencias de atajos

- [Windows: métodos abreviados de teclado](https://support.microsoft.com/es-es/accessibility/windows/keyboard-shortcuts-in-windows)
- [Word: seleccionar texto](https://support.microsoft.com/es-es/word/select-text)
- [Excel: métodos abreviados de teclado](https://support.microsoft.com/es-es/accessibility/excel/keyboard-shortcuts-in-excel)
- [MediaPipe: Gesture Recognizer y categorías estándar](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/GestureRecognizerOptions)
