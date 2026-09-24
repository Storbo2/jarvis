# Asistente Jarvis

Experimento personal para controlar Windows mediante gestos de mano y voz. El objetivo es aprender construyendo un asistente de escritorio con efecto futurista, empezando por una demo segura de visión por computadora.

## Estado actual

La versión actual permite:

- abrir una cámara conectada al equipo;
- detectar una mano y dibujar sus 21 landmarks;
- mostrar lateralidad y confianza de la detección;
- reconocer índice, pinza y palma abierta, además de pulgar arriba, V y C;
- mover el mouse, hacer clic y arrastrar con una mano;
- copiar y pegar con C y V sostenidas;
- liberar el botón y desactivar el control con la palma abierta;
- mostrar FPS y salir de forma segura con `Q` o `Esc`.

El pulgar arriba se muestra en pantalla. El dictado se agregará después.

## Hoja de ruta

1. ~~Abrir la cámara, detectar una mano y visualizar sus 21 landmarks.~~
2. ~~Reconocer gestos básicos con geometría (índice, pinza, palma abierta).~~
3. ~~Añadir control de cursor y mouse con suavizado y un gesto de parada global.~~
4. Afinar la calibración y la estabilidad temporal con pruebas de uso.
5. Explorar dictado, formato de puntuación y atajos de teclado.
6. ~~Añadir acciones de copiar y pegar para los gestos C y V.~~

El STOP global debe liberar cualquier botón sostenido y cancelar acciones activas. No habilitar control del sistema hasta que la vista previa de landmarks sea estable.

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
**recolocación**: señala y mueve el cursor; luego deja de señalar (mano neutra),
vuelve la mano a una posición cómoda y señala de nuevo. El cursor queda quieto
mientras recolocas la mano. Puedes repetirlo tantas veces como necesites.

Para copiar, selecciona texto con el mouse y mantén la C durante al menos 0,45
segundos. Para pegar, enfoca el campo de destino y mantén la V el mismo tiempo.
Cada gesto envía una sola combinación de teclas; suéltalo y vuelve a formarlo
para repetir. La ventana muestra `Ctrl+C enviado` o `Ctrl+V enviado` al activarse.
Las combinaciones se envían a la aplicación que tenga el foco en Windows.

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
| Mano curvada en forma de C | `C (EXPERIMENTAL)`: copiar |

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
