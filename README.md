# Asistente Jarvis

Experimento personal para controlar Windows mediante gestos de mano y voz. El objetivo es aprender construyendo un asistente de escritorio con efecto futurista, empezando por una demo segura de visión por computadora.

## Hoja de ruta

1. Abrir la cámara, detectar una mano y visualizar sus 21 landmarks.
2. Reconocer gestos básicos con geometría y estados (índice, pinza, palma abierta).
3. Añadir control de cursor y mouse con suavizado y un gesto de parada global.
4. Explorar dictado, formato de puntuación y atajos de teclado.
5. Evaluar gestos adicionales para copiar y pegar.

El STOP global debe liberar cualquier botón sostenido y cancelar acciones activas. No habilitar control del sistema hasta que la vista previa de landmarks sea estable.

## Requisitos

- Windows 10/11 y Python 3.11 o posterior.
- [`uv`](https://docs.astral.sh/uv/) y Git.
- Cámara y micrófono para las fases correspondientes.

Dependencias de cámara, visión, audio y control se agregarán al avanzar cada fase, evitando instalar modelos o librerías que aún no se usan.

## Empezar

```powershell
uv sync
uv run python -m asistente_jarvis --help
```

Al clonar el repositorio, `uv sync` creará el entorno virtual y el lockfile según el `pyproject.toml`.

## Estructura

```text
src/asistente_jarvis/
  vision/    captura de cámara y seguimiento de manos
  gestures/  geometría, detección y estados
  controls/  adaptadores de mouse y teclado
  speech/    grabación, transcripción y formato
  config/    configuración local
  __main__.py
  cli.py
 tests/
data/        datos locales, excluidos de Git
```

Modelos descargados, pesos, grabaciones y datos de entrenamiento van en `models/`, `data/` o `artifacts/`; esas rutas quedan fuera de Git. Los archivos pequeños de configuración de ejemplo sí se versionan.
