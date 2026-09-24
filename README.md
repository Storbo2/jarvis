# Asistente Jarvis

Experimento personal para controlar Windows mediante gestos de mano y voz. El objetivo es aprender construyendo un asistente de escritorio con efecto futurista, empezando por una demo segura de visión por computadora.

## Estado actual

La versión preliminar ya permite:

- abrir una cámara conectada al equipo;
- detectar una mano y dibujar sus 21 landmarks;
- mostrar lateralidad y confianza de la detección;
- reconocer de forma geométrica índice levantado, pinza y palma abierta;
- mostrar FPS y salir de forma segura con `Q` o `Esc`.

Esta versión solo observa y clasifica. Todavía no mueve el cursor ni envía entradas al
sistema operativo.

## Hoja de ruta

1. ~~Abrir la cámara, detectar una mano y visualizar sus 21 landmarks.~~
2. ~~Reconocer gestos básicos con geometría (índice, pinza, palma abierta).~~
3. Añadir estabilidad temporal, calibración y una máquina de estados.
4. Añadir control de cursor y mouse con suavizado y un gesto de parada global.
5. Explorar dictado, formato de puntuación y atajos de teclado.
6. Evaluar gestos adicionales para copiar y pegar.

El STOP global debe liberar cualquier botón sostenido y cancelar acciones activas. No habilitar control del sistema hasta que la vista previa de landmarks sea estable.

## Requisitos

- Windows 10/11 y Python 3.11 o 3.12. El archivo `.python-version` fija Python 3.12
  para mantener compatibilidad con MediaPipe.
- [`uv`](https://docs.astral.sh/uv/) y Git.
- Cámara y micrófono para las fases correspondientes.

Dependencias de cámara, visión, audio y control se agregarán al avanzar cada fase, evitando instalar modelos o librerías que aún no se usan.

## Empezar

```powershell
uv sync
uv run asistente-jarvis download-model
uv run asistente-jarvis preview
```

Al clonar el repositorio, `uv sync` creará el entorno virtual según el `uv.lock`.
El modelo se guarda en `models/hand_landmarker.task`, una ruta excluida de Git.

Durante la vista previa prueba estos gestos frente a la cámara:

| Gesto | Etiqueta preliminar |
|---|---|
| Índice extendido y otros tres dedos plegados | `INDICE` |
| Pulgar e índice juntos | `PINZA` |
| Cinco dedos extendidos | `STOP / PALMA ABIERTA` |

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
  controls/  adaptadores de mouse y teclado
  speech/    grabación, transcripción y formato
  config/    configuración local
  __main__.py
  cli.py
 tests/
data/        datos locales, excluidos de Git
```

Modelos descargados, pesos, grabaciones y datos de entrenamiento van en `models/`, `data/` o `artifacts/`; esas rutas quedan fuera de Git. Los archivos pequeños de configuración de ejemplo sí se versionan.
