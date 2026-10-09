# Asistente Jarvis

Experimento personal para controlar Windows mediante gestos de mano y voz. El objetivo es aprender construyendo un asistente de escritorio con efecto futurista, empezando por una demo segura de visión por computadora.

## Estado actual

La versión actual permite:

- abrir una cámara conectada al equipo;
- detectar hasta dos manos y dibujar sus 21 landmarks;
- mostrar lateralidad y confianza de la detección;
- reconocer índice, pinza y palma abierta, además de pulgar arriba/abajo, pulgar lateral, V, C e `ILoveYou`;
- mover el mouse, hacer clic izquierdo, doble clic, clic derecho y arrastrar con una mano;
- copiar y pegar con C y V sostenidas, y seleccionar todo con una V invertida;
- controlar el zoom con dos pinzas, una en cada mano;
- recolocar la mano con un puño frontal, sin interferir con la pinza;
- desplazar la página, cambiar de aplicación, controlar multimedia y deshacer o rehacer usando dos manos;
- tomar, mover, maximizar y encajar la ventana activa usando una garra y la otra mano;
- iniciar el recorte de pantalla con `ILoveYou` y mostrar avisos breves sobre el escritorio;
- dictar con pulgar arriba, transcribir localmente con Whisper large-v3 y escribir en la ventana activa;
- activar órdenes de voz diciendo «Hey Jarvis» y abrir aplicaciones desde el menú Inicio;
- liberar el botón y desactivar el control con dos palmas abiertas sostenidas;
- mostrar FPS y salir de forma segura con `Ctrl+Q`.

Consulta [GESTURES.md](GESTURES.md) para la lista completa de gestos y funciones.
Consulta [CALIBRATION.md](CALIBRATION.md) para calibrar cada equipo y probar
uno o varios monitores.

## Hoja de ruta

1. ~~Abrir la cámara, detectar una mano y visualizar sus 21 landmarks.~~
2. ~~Reconocer gestos básicos con geometría (índice, pinza, palma abierta).~~
3. ~~Añadir control de cursor y mouse con suavizado y un gesto de parada global.~~
4. Afinar la calibración y la estabilidad temporal con pruebas de uso.
5. ~~Agregar dictado local y escritura en la ventana activa.~~ Afinar puntuación y formato.
6. ~~Añadir acciones de copiar y pegar para los gestos C y V.~~

El STOP global libera cualquier botón sostenido y cancela las acciones activas.

## Requisitos

- Windows 10/11 y Python 3.11 o 3.12. El archivo `.python-version` fija Python 3.12
  para mantener compatibilidad con MediaPipe.
- [`uv`](https://docs.astral.sh/uv/) y Git.
- Cámara y micrófono para el control por gestos y dictado.

El control del mouse usa PyAutoGUI y el dictado captura el micrófono con
`sounddevice`.

## Empezar

```powershell
uv sync
uv run asistente-jarvis download-model
uv run asistente-jarvis preview
```

Para controlar el mouse:

```powershell
uv run asistente-jarvis control
```

El control empieza pausado. Pulsa `F8` para activarlo; `F8` vuelve a pausarlo.
Este atajo funciona aunque estés haciendo clic en otra ventana. `Ctrl+Q`
cierra el programa; `Esc` queda disponible para la aplicación activa. Mantén
ambas palmas abiertas **2 segundos** para hacer STOP, cancelar el dictado y pausar
el control; pulsa `F8` para reactivarlo. Al sacar las manos del encuadre se
libera cualquier arrastre y se detiene el cursor, pero el control queda activo.
Las esquinas de la pantalla conservan el mecanismo de seguridad de PyAutoGUI.
La cámara se abre como un panel compacto de 480×360 siempre visible, desplazado
desde los bordes superior y derecho para no bloquear botones ni barras de
desplazamiento. Puedes moverlo o redimensionarlo manualmente. Su cabecera,
colores cian y naranja y estados `ONLINE`/`STANDBY` forman la primera versión
del estilo visual de Jarvis.

Con el control activo, señala con el índice y mueve la mano para desplazar el
cursor desde su posición actual. La posición permanece quieta al formar una
pinza: si sueltas antes de 0,45 segundos, hace clic exactamente allí. Si mantienes
la pinza, comienza el arrastre desde esa posición; mueve la mano y suelta la
pinza para terminar. Al volver a señalar, el cursor retoma el movimiento desde
donde quedó, sin saltar a otra posición.
El movimiento combina la punta y dos articulaciones del índice. Una mediana de
tres imágenes descarta saltos aislados; el suavizado se adapta a la velocidad:
estabiliza el cursor en reposo y responde más rápido a movimientos amplios.
Este filtro se reinicia al dejar de señalar, para que volver al índice no
desplace el cursor de golpe. El arrastre por pinza conserva su propio movimiento.

Para hacer clic derecho, mantén extendido el índice, levanta el dedo medio y
junta su punta con el pulgar durante 0,32 segundos. Anular y meñique pueden
quedar plegados. El índice debe permanecer separado del pulgar para distinguirlo
de la pinza izquierda. El dedo medio levantado evita que el pulgar apoyado sobre
una mano cerrada se interprete como clic. Se ejecuta una vez y debes
separar los dedos antes de repetir. `F10` muestra las proporciones de ambas
pinzas y si la postura del medio está lista para facilitar el ajuste.

Pulsa `F9` en `control` para abrir el panel de calibración. Ajusta **sensibilidad**
(distancia recorrida), **estabilidad** (suavidad del índice) y **zona muerta**
(movimientos mínimos que se ignoran). Mientras el panel está abierto, los
gestos no ejecutan acciones. `F9` o cerrar el panel guarda los valores en
`data/cursor_calibration.json`, excluido de Git. Cierra el panel para probar el
cursor y vuelve a abrirlo si quieres retocar. `F10` muestra u oculta en la
cámara un diagnóstico con el punto bruto (amarillo), filtrado (cian), destino
y posición real del cursor; también aparece mientras calibras. El diagnóstico
usa coordenadas de la cámara para los puntos y píxeles de pantalla para el
destino y la posición real.

La sensibilidad inicial es `0.8`. Si necesitas movimientos más finos,
prueba `uv run asistente-jarvis control --sensitivity 0.6`. Ese argumento
reemplaza la sensibilidad guardada durante esa ejecución. Un valor mayor mueve
el cursor más lejos por el mismo desplazamiento de mano (rango admitido: `0.1` a
`4.0`). En un monitor grande empieza por `--sensitivity 1.5` y ajusta desde ahí.
Un valor muy alto también amplifica los pequeños temblores.

Para alcanzar zonas lejanas sin aumentar tanto la sensibilidad, usa la
**recolocación**: señala y mueve el cursor; luego cierra el puño con los
nudillos apuntando a la cámara, como si fueras a golpear la pantalla. Mueve
la mano a una posición cómoda y vuelve a señalar. El cursor queda quieto
mientras recolocas la mano. Una mano cerrada sin esa orientación se muestra
como `MANO CERRADA` y no tiene prioridad sobre la pinza.

Para copiar, selecciona texto con el mouse y mantén la C durante al menos 0,45
segundos. Para pegar, enfoca el campo de destino y mantén la V con el pulgar
plegado el mismo tiempo. Si el pulgar está levantado, se muestra `PREPARANDO
PINZA` y no se envía `Ctrl+V`, lo que permite pasar entre las pinzas izquierda
y derecha sin pegar accidentalmente.
Cada gesto envía una sola combinación de teclas; suéltalo y vuelve a formarlo
para repetir. La ventana muestra `Ctrl+C enviado` o `Ctrl+V enviado` al activarse.
Las combinaciones se envían a la aplicación que tenga el foco en Windows.

Para seleccionar todo, gira la V hacia abajo como una A y mantenla durante
0,45 segundos. En el Explorador de archivos y en Word, Excel y PowerPoint de
escritorio se envía `Ctrl+E`; en otras aplicaciones se envía `Ctrl+A`. Puedes forzar una opción con
`--select-all-mode ctrl-e` o `--select-all-mode ctrl-a`.

Para zoom, muestra una pinza con cada mano durante 0,35 segundos. Separa las
manos para acercar y júntalas para alejar. Se envían `Ctrl` más suma o resta
del teclado numérico; la aplicación activa debe admitir esos atajos. Con dos
manos visibles se suspenden los controles de una mano. STOP requiere ambas
palmas abiertas durante dos segundos.

Con un puño fijo y el índice de la otra mano puedes desplazar vertical u
horizontalmente. Con un puño fijo y una V en la otra mano se abre `Alt+Tab`
después de 0,28 s; inclina la mano unos 10° en el plano de la cámara hacia un
lado para recorrer las ventanas. El primer cruce avanza inmediatamente y
mantener la inclinación repite los pasos con más velocidad cuanto mayor sea el giro.
Suelta el puño para seleccionar. STOP, `F8` y la pérdida de una mano
sueltan `Alt`. Con un puño y el pulgar de la otra mano hacia la izquierda o la
derecha se envía `Ctrl+Z` o `Ctrl+Y`, respectivamente.
Si el detector confunde ese puño con una pinza, el control de dos manos usa
el gesto de la otra mano para mantener el puño como modificador. Dos pinzas
siguen reservadas para el zoom.

Un puño con pulgar arriba o abajo ajusta el volumen; mantenlo para repetir.
Un puño con la otra palma abierta reproduce o pausa. Un puño con índice y meñique
extendidos, inclinados levemente a la izquierda o derecha, selecciona la pista anterior
o siguiente. Consulta [GESTURES.md](GESTURES.md) para las posiciones exactas.

Para mover la ventana activa, muestra una sola mano y forma una **garra** con
todos los dedos plegados y las puntas hacia la cámara durante 0,52 s. La ventana se toma por la barra de
título y se restaura si estaba maximizada. Mantén la garra para arrastrarla;
abre esa mano para maximizarla o levanta solamente el índice para soltarla y
retomar el cursor. Mientras la tomas, señala con la otra mano a
izquierda/derecha para una mitad. Con más de un
monitor, lleva la garra desde el centro hasta el borde de la cámara para enviar
la ventana al monitor vecino. La garra no inicia la toma cuando hay dos manos,
por lo que el puño modificador conserva prioridad en los controles multimedia.
Un movimiento rápido de la garra hacia la parte inferior minimiza la ventana y
libera el cursor. La detección combina velocidad, recorrido y posición final
medidos sobre varios fotogramas para reconocer un descenso firme sin exigir un
pico de velocidad difícil de reproducir.
El modo F11 de un navegador debe salir antes con
su atajo propio.

Mantener `ILoveYou` con una mano durante 0,45 segundos abre el recorte de
pantalla de Windows (`Win+Shift+S`). Señala con el índice para colocar el cursor,
luego haz una pinza, mueve la mano sin soltarla y abre la pinza para completar
el recorte. Esta pinza inicia el arrastre de inmediato. Los comandos puntuales muestran un aviso
pequeño sobre el escritorio durante 1,6 segundos, también cuando trabajas en
otra ventana.

## Dictado con Whisper

Instala las dependencias y prepara el modelo local `large-v3` con:

```powershell
uv sync
uv run asistente-jarvis prepare-speech
```

El modelo queda en `models/whisper/large-v3/` y no se versiona. En `control`,
activa el sistema con `F8` y deja enfocado el campo donde quieres escribir.
Mantén **pulgar arriba 0,6 segundos** para empezar y **pulgar abajo 0,6 segundos**
para terminar. Mientras grabas, el audio se procesa al detectar una pausa breve
o, como máximo, cada tres segundos y el texto aparece en el campo
enfocado. Al terminar, se procesan los fragmentos restantes. La grabación tiene
un límite de 60 segundos. Durante el dictado se suspenden el mouse y los otros
gestos; dos palmas sostenidas 2 segundos o `F8` cancelan. El primer fragmento puede tardar más al cargar el
modelo. El audio se mantiene en memoria y no se guarda en disco.

Whisper puede agregar signos por su cuenta. Jarvis descarta esos signos y
escribe puntuación cuando dices **«coma»** (`,`), **«punto»** (`.`) o
**«dos puntos»** (`:`). **«Enter»** hace `Shift+Enter` para insertar un salto
de línea sin enviar el mensaje. **«Enviar»** hace `Enter` normal cuando se
reconoce como orden aislada o después de una pausa que Whisper haya marcado
con puntuación. Di «Enviar» separado de la frase anterior para evitar confundirlo
con la palabra «enviar» dentro de una oración. **«Borrar palabra»** envía
`Ctrl+Backspace`; **«Borrar todo»** envía `Ctrl+A` y `Backspace` al campo activo.
Estas dos órdenes de borrado también deben decirse solas.
Whisper aún puede convertir una orden hablada directamente en un signo; en ese
caso no es posible distinguirlo de un signo inferido y no se escribe.

El texto se escribe como Unicode en la misma ventana que tenía el foco al
iniciar la grabación. Si cambias de ventana antes de terminar, se evita escribir
en un lugar equivocado y el texto aparece en la consola. Algunas aplicaciones
con permisos elevados pueden rechazar la escritura simulada desde un proceso
normal. Para usar otro micrófono, ejecuta `control --microphone N` con el índice
del dispositivo; `--speech-language en` cambia el idioma. `--speech-device auto`
intenta CUDA y, si no puede cargarlo, usa CPU. También puedes forzar `cuda` o
`cpu`. En este equipo el programa busca primero las DLL de CUDA 12 y cuDNN 9
que ya están en la instalación global de PyTorch, las añade al `PATH` de este
proceso y las carga antes de iniciar Whisper. También se puede indicar
otra carpeta con la variable `JARVIS_CUDA_DLL_DIR`. El modo `auto` cambia a CPU
si CUDA falla incluso durante la primera transcripción. En CPU, `large-v3`
puede ir considerablemente más lento que el habla, por lo que el texto seguirá
apareciendo por fragmentos, pero con retraso. Para acercarse al tiempo real con
este modelo, Windows debe encontrar CUDA 12 (cuBLAS) y cuDNN 9 en este entorno
Python. [faster-whisper documenta esos requisitos](https://github.com/SYSTRAN/faster-whisper#gpu).

## Órdenes de voz «Hey Jarvis»

`control` mantiene activo un detector local pequeño de la frase **«Hey Jarvis»**.
Al reconocerla, captura la frase siguiente, la transcribe con el mismo Whisper
large-v3 y busca una aplicación usando el menú Inicio de Windows. Por ejemplo:

```text
Hey Jarvis … abre Spotify
```

La detección de activación no necesita cuenta ni clave. Su modelo reconoce la
frase inglesa completa «Hey Jarvis»; después, Whisper procesa la orden en
español. Las primeras órdenes pueden tardar más mientras se carga large-v3 en
CUDA. En este equipo el detector de activación consume CPU de forma continua,
mientras Whisper solo trabaja después de la frase de activación. El audio se
mantiene en memoria y no se envía a servicios remotos.

Prepara una vez los modelos ligeros de openWakeWord:

```powershell
uv run asistente-jarvis prepare-wake-word
```

El comando descarga alrededor de 9 MB en los recursos de
openWakeWord dentro del entorno `.venv`. `uv sync` instala automáticamente la
dependencia `openwakeword` y su runtime ONNX. Las órdenes están limitadas por
ahora a abrir una aplicación con «abre», «inicia» o «lanza» más su nombre.
Windows busca ese nombre entre las aplicaciones registradas en Inicio; la
aplicación debe aparecer en la búsqueda del sistema. Esta versión no ejecuta
comandos arbitrarios ni accede a archivos.

La frase de activación está entrenada para inglés; pronunciada como «Hey
Yarvis» puede requerir probar varias veces o ajustar el umbral en una siguiente
iteración. El modelo Hey Jarvis de openWakeWord está publicado con licencia
CC BY-NC-SA 4.0, adecuada para este uso personal.

Para desactivar la escucha continua en una ejecución:

```powershell
uv run asistente-jarvis control --no-voice-assistant
```

Durante el dictado iniciado con pulgar arriba, el detector suelta el micrófono;
lo retoma al terminar o cancelar el dictado. Para escoger el micrófono de voz,
usa el mismo `--microphone N` que en el dictado. El micrófono Realtek se elige
automáticamente cuando está disponible.

El programa prefiere el micrófono Realtek de la captura; en este equipo aparece
como índice `1` y también es la entrada predeterminada de Python. Si cambia,
consulta los índices con
`uv run python -c "import sounddevice as sd; print(sd.query_devices())"` y pasa
el índice de entrada con `--microphone N`. Windows debe permitir el acceso al
micrófono para aplicaciones de escritorio.

Al clonar el repositorio, `uv sync` creará el entorno virtual según el `uv.lock`.
El modelo se guarda en `models/hand_landmarker.task`, una ruta excluida de Git.

Durante la vista previa prueba estos gestos frente a la cámara:

| Gesto | Etiqueta preliminar |
|---|---|
| Índice extendido y otros tres dedos plegados | `INDICE` |
| Pulgar e índice juntos | `PINZA` |
| Pulgar y medio juntos, con el índice extendido | `PINZA MEDIA / CLIC DERECHO` |
| Cuatro dedos extendidos, juntos o separados; pulgar libre | `PALMA ABIERTA` |
| Pulgar arriba y demás dedos plegados | `PULGAR ARRIBA` |
| Índice y medio extendidos y separados | `V / DOS DEDOS`: pegar |
| Índice y medio extendidos, separados y apuntando hacia abajo | `A / V INVERTIDA`: seleccionar todo |
| Mano curvada en forma de C | `C (EXPERIMENTAL)`: copiar |
| Puño con nudillos hacia la cámara | `PUNO FRONTAL / RECOLOCAR` |
| Mano cerrada normal | `MANO CERRADA` |
| Pulgar extendido a un lado | `PULGAR IZQUIERDA` o `PULGAR DERECHA` |
| Pulgar, índice y meñique extendidos | `ILOVEYOU / RECORTE` |

Si la cámara principal no corresponde al índice `0`, prueba:

```powershell
uv run asistente-jarvis preview --camera 1
```

En Windows también puedes forzar DirectShow si el backend automático falla:

```powershell
uv run asistente-jarvis preview --backend dshow
```

Consulta todas las opciones con `uv run asistente-jarvis preview --help`.

## Estructura

```text
src/asistente_jarvis/
  application/ intenciones semánticas, resolución y ejecución de acciones
  vision/    captura, modelo, seguimiento de manos y vista previa
  gestures/  geometría y clasificación preliminar
  controls/  control de mouse y atajos
  speech/    grabación, transcripción y formato
  config/    configuración local
  __main__.py
  cli.py
tests/
data/        datos locales, excluidos de Git
```

Los controladores de gestos producen intenciones como `copy`, `zoom_in` o
`switch_next` sin enviar teclas directamente. `IntentResolver` coordina los
estados de una y dos manos; `ActionDispatcher` es el único punto que ejecuta
atajos, rueda y modificadores en Windows. Este último conserva en memoria las
50 acciones recientes y garantiza que `Alt` se libere al pausar, hacer STOP,
perder una mano o cerrar el programa.

Modelos descargados, pesos, grabaciones y datos de entrenamiento van en `models/`, `data/` o `artifacts/`; esas rutas quedan fuera de Git. Los archivos pequeños de configuración de ejemplo sí se versionan.
