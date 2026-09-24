from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture, recognize_gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint
from asistente_jarvis.vision.hand_tracker import HandObservation, HandTracker


HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)


@dataclass(frozen=True, slots=True)
class PreviewOptions:
    camera_index: int
    backend: str
    mirror: bool
    model_path: Path


def _open_camera(cv2: object, index: int, backend: str) -> object:
    backend_constants = {
        "dshow": "CAP_DSHOW",
        "msmf": "CAP_MSMF",
    }
    if backend == "auto":
        capture = cv2.VideoCapture(index)
    else:
        constant_name = backend_constants[backend]
        backend_id = getattr(cv2, constant_name, None)
        if backend_id is None:
            raise RuntimeError(
                f"Esta instalación de OpenCV no ofrece el backend {backend}. "
                "Ejecuta de nuevo `uv sync` o usa `--backend auto`."
            )
        capture = cv2.VideoCapture(index, backend_id)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(
            f"No fue posible abrir la cámara {index}. Prueba otro índice con `--camera 1` "
            "o un backend con `--backend dshow`."
        )
    return capture


def _pixel(point: NormalizedPoint, width: int, height: int) -> tuple[int, int]:
    return int(point.x * width), int(point.y * height)


def _draw_hand(cv2: object, frame: object, observation: HandObservation) -> Gesture:
    height, width = frame.shape[:2]
    result = recognize_gesture(observation.landmarks)
    color = (0, 90, 255) if result.gesture is Gesture.OPEN_PALM else (40, 220, 120)

    for start, end in HAND_CONNECTIONS:
        cv2.line(
            frame,
            _pixel(observation.landmarks[start], width, height),
            _pixel(observation.landmarks[end], width, height),
            (180, 180, 180),
            2,
            cv2.LINE_AA,
        )
    for point in observation.landmarks:
        cv2.circle(frame, _pixel(point, width, height), 4, color, -1, cv2.LINE_AA)

    title = f"{result.label}  |  {observation.handedness} {observation.confidence:.0%}"
    cv2.rectangle(frame, (12, 12), (min(width - 12, 520), 55), (20, 20, 20), -1)
    cv2.putText(frame, title, (24, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
    return result.gesture


def run_preview(options: PreviewOptions) -> int:
    import cv2

    capture = _open_camera(cv2, options.camera_index, options.backend)
    started_at = monotonic()
    last_frame_at = started_at
    fps = 0.0

    try:
        with HandTracker(options.model_path) as tracker:
            while True:
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError("La cámara dejó de entregar imágenes.")
                if options.mirror:
                    frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp_ms = int((monotonic() - started_at) * 1000)
                observations = tracker.detect(rgb, timestamp_ms)
                for observation in observations:
                    _draw_hand(cv2, frame, observation)

                now = monotonic()
                instant_fps = 1 / max(now - last_frame_at, 1e-6)
                fps = instant_fps if fps == 0 else fps * 0.9 + instant_fps * 0.1
                last_frame_at = now
                cv2.putText(
                    frame,
                    f"{fps:.0f} FPS | Q o ESC para salir",
                    (16, frame.shape[0] - 18),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (240, 240, 240),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("Asistente Jarvis - Reconocimiento preliminar", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    return 0
    finally:
        capture.release()
        cv2.destroyAllWindows()
