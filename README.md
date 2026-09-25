# Asistente Jarvis

Experimento personal para controlar Windows mediante gestos de mano y voz. El objetivo es aprender construyendo un asistente de escritorio con efecto futurista, empezando por una demo segura de visión por computadora.

## Estado actual

La versión actual permite:

- abrir una cámara conectada al equipo;
- detectar hasta dos manos y dibujar sus 21 landmarks;
- mostrar lateralidad y confianza de la detección;
- reconocer índice, pinza y palma abierta, además de pulgar arriba, V y C;
- mover el mouse, hacer clic y arrastrar con una mano;
- copiar y pegar con C y V sostenidas, y seleccionar todo con una V invertida;
- controlar el zoom con dos pinzas, una en cada mano;
- recolocar la mano con un puño cerrado;
- desplazar la página y cambiar de aplicación usando dos manos;
- liberar el botón y desactivar el control con la palma abierta;
- mostrar FPS y salir de forma segura con `Q` o `Esc`.

El pulgar arriba se muestra en pantalla. El dictado se agregará después.
Consulta [GESTURES.md](GESTURES.md) para la lista completa de gestos y funciones.

## Hoja de ruta

1. ~~Abrir la cámara, detectar una mano y visualizar sus 21 landmarks.~~
2. ~~Reconocer gestos básicos con geometría (índice, pinza, palma abierta).~~
3. ~~Añadir control de cursor y mouse con suavizado y un gesto de parada global.~~
4. Afinar la calibración y la estabilidad temporal con pruebas de uso.
5. Explorar dictado, formato de puntuación y atajos de teclado.
6. ~~Añadir acciones de copiar y pegar para los gestos C y V.~~

El STOP global libera cualquier botón sostenido y cancela las acciones activas.

## Requisitos

- Windows 10/11 y Python 3.11 o 3.12. El archivo `.python-version` fija Python 3.12
  para mantener compatibilidad con MediaPipe.
- [`uv`](https://docs.astral.sh/uv/) y Git.
- Cámara y micrófono para las fases correspondientes.

El control del mouse usa PyAutoGUI. El micrófono se incorporará cuando llegue la
fase de dictado.

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
Este atajo funciona aunque estés haciendo clic en otra ventana. `Esc` cierra el
programa; también funciona fuera de la ventana de cámara. La palma abierta
detiene el control y suelta cualquier arrastre: pulsa `F8` para reactivarlo.
Si se pierde la mano durante 0,35 segundos, el control también se pausa y libera
el botón. Las esquinas de la pantalla conservan el mecanismo de seguridad de
PyAutoGUI.

Con el control activo, señala con el índice y mueve la mano para desplazar el
cursor desde su posición actual. La posición permanece quieta al formar una
pinza: si sueltas antes de 0,45 segundos, hace clic exactamente allí. Si mantienes
la pinza, comienza el arrastre desde esa posición; mueve la mano y suelta la
pinza para terminar. Al volver a señalar, el cursor retoma el movimiento desde
donde quedó, sin saltar a otra posición.

La sensibilidad predeterminada es `0.8`. Si necesitas movimientos más finos,
prueba `uv run asistente-jarvis control --sensitivity 0.6`. Un valor mayor mueve
el cursor más lejos por el mismo desplazamiento de mano (rango admitido: `0.1` a
`4.0`). En un monitor grande empieza por `--sensitivity 1.5` y ajusta desde ahí.
Un valor muy alto también amplifica los pequeños temblores.

Para alcanzar zonas lejanas sin aumentar tanto la sensibilidad, usa la
**recolocación**: señala y mueve el cursor; luego cierra el puño, mueve la mano
a una posición cómoda y vuelve a señalar. El cursor queda quieto mientras
recolocas la mano. Puedes repetirlo tantas veces como necesites.

Para copiar, selecciona texto con el mouse y mantén la C durante al menos 0,45
segundos. Para pegar, enfoca el campo de destino y mantén la V el mismo tiempo.
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
manos visibles se suspenden los controles de una mano. STOP funciona con
cualquiera de las dos manos.

Con un puño fijo y el índice de la otra mano puedes desplazar vertical u
horizontalmente. Con un puño fijo y una V en la otra mano se abre `Alt+Tab`;
mueve la V a los lados para recorrer las ventanas y suelta el puño para
seleccionar. STOP, `F8`, `Esc` y la pérdida de una mano sueltan `Alt`.

## Voz preparada para la siguiente fase

La dependencia `faster-whisper` y el modelo convertido `large-v3` se
preparan con:

```powershell
uv sync
uv run asistente-jarvis prepare-speech
```

El modelo queda en `models/whisper/large-v3/` y no se versiona. Esta fase solo
descarga los pesos y deja resueltas las librerías: no captura micrófono ni
transcribe todavía. Para utilizar la GPU con la versión actual de CTranslate2,
Windows debe poder encontrar CUDA 12 (cuBLAS) y cuDNN 9. Comprueba esa
compatibilidad cuando implementemos el dictado; el funcionamiento anterior de
Subtitle Edit no confirma por sí solo que estas DLL estén disponibles para
este entorno Python.

Al clonar el repositorio, `uv sync` creará el entorno virtual según el `uv.lock`.
El modelo se guarda en `models/hand_landmarker.task`, una ruta excluida de Git.

Durante la vista previa prueba estos gestos frente a la cámara:

| Gesto | Etiqueta preliminar |
|---|---|
| Índice extendido y otros tres dedos plegados | `INDICE` |
| Pulgar e índice juntos | `PINZA` |
| Cuatro dedos extendidos, juntos o separados; pulgar libre | `STOP / PALMA ABIERTA` |
| Pulgar arriba y demás dedos plegados | `PULGAR ARRIBA` |
| Índice y medio extendidos y separados | `V / DOS DEDOS`: pegar |
| Índice y medio extendidos, separados y apuntando hacia abajo | `A / V INVERTIDA`: seleccionar todo |
| Mano curvada en forma de C | `C (EXPERIMENTAL)`: copiar |
| Puño cerrado | `PUNO / RECOLOCAR` |

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

Modelos descargados, pesos, grabaciones y datos de entrenamiento van en `models/`, `data/` o `artifacts/`; esas rutas quedan fuera de Git. Los archivos pequeños de configuración de ejemplo sí se versionan.
