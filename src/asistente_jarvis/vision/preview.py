from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from asistente_jarvis.controls.mouse import MouseController, MouseSettings
from asistente_jarvis.controls.shortcuts import ShortcutController, ShortcutSettings
from asistente_jarvis.controls.zoom import ZoomController
from asistente_jarvis.gestures.detector import Gesture, GestureResult, recognize_gesture
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
    control_mouse: bool = False
    sensitivity: float = 0.8
    select_all_mode: str = "auto"


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


def _draw_hand(
    cv2: object, frame: object, observation: HandObservation, *, line: int = 0
) -> GestureResult:
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
    top = 12 + line * 44
    cv2.rectangle(frame, (12, top), (min(width - 12, 520), top + 43), (20, 20, 20), -1)
    cv2.putText(frame, title, (24, top + 31), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
    return result


def run_preview(options: PreviewOptions) -> int:
    import cv2
    import ctypes
    import pyautogui

    mouse = MouseController(MouseSettings(sensitivity=options.sensitivity)) if options.control_mouse else None
    shortcuts = (
        ShortcutController(ShortcutSettings(select_all_mode=options.select_all_mode))
        if options.control_mouse
        else None
    )
    zoom = ZoomController() if options.control_mouse else None
    capture = _open_camera(cv2, options.camera_index, options.backend)
    user32 = ctypes.windll.user32 if mouse is not None else None
    f8_was_down = False
    started_at = monotonic()
    last_frame_at = started_at
    fps = 0.0
    shortcut_feedback: tuple[str, float] | None = None
    waiting_for_pinch_release = False

    try:
        with HandTracker(options.model_path, num_hands=2) as tracker:
            while True:
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError("La cámara dejó de entregar imágenes.")
                if options.mirror:
                    frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp_ms = int((monotonic() - started_at) * 1000)
                observations = tracker.detect(rgb, timestamp_ms)
                results = [
                    _draw_hand(cv2, frame, observation, line=index)
                    for index, observation in enumerate(observations)
                ]

                if mouse is not None:
                    f8_is_down = bool(user32.GetAsyncKeyState(0x77) & 0x8000)
                    if f8_is_down and not f8_was_down:
                        if mouse.armed:
                            mouse.stop()
                        else:
                            mouse.arm()
                    f8_was_down = f8_is_down
                    if user32.GetAsyncKeyState(0x1B) & 0x8000:
                        return 0
                    action = None
                    if len(observations) == 2:
                        waiting_for_pinch_release = True
                        mouse.cancel_gesture()
                        shortcuts.reset()
                        if any(result.gesture is Gesture.OPEN_PALM for result in results):
                            mouse.stop()
                            zoom.reset()
                        else:
                            action = zoom.update(
                                (results[0].gesture, results[1].gesture),
                                (observations[0].landmarks[8], observations[1].landmarks[8]),
                                armed=mouse.armed,
                            )
                    else:
                        zoom.reset()
                        gesture = results[0].gesture if results else None
                        landmarks = observations[0].landmarks if observations else None
                        pinch_ratio = results[0].pinch_ratio if results else None
                        if waiting_for_pinch_release and gesture is Gesture.PINCH:
                            mouse.cancel_gesture()
                            shortcuts.reset()
                        else:
                            if gesture is not None:
                                waiting_for_pinch_release = False
                            mouse.update(gesture, landmarks, pinch_ratio=pinch_ratio)
                            action = shortcuts.update(
                                gesture,
                                armed=mouse.armed,
                                dragging=mouse.dragging,
                            )
                    if not mouse.armed:
                        shortcut_feedback = None
                    if action is not None:
                        shortcut_feedback = (action, monotonic())

                    if mouse.dragging:
                        status = "ARRASTRANDO"
                    elif not mouse.armed:
                        status = "PAUSADO"
                    elif len(observations) == 2:
                        status = "ZOOM 2 MANOS" if all(
                            result.gesture is Gesture.PINCH for result in results
                        ) else "2 MANOS"
                    elif not results or results[0].gesture is Gesture.UNKNOWN:
                        status = "RECOLOCA LA MANO"
                    else:
                        status = "ACTIVO"
                    status_y = 82 + max(0, len(observations) - 1) * 44
                    cv2.putText(
                        frame,
                        f"MOUSE: {status} | F8 activar/pausar | ESC salir",
                        (16, status_y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 90, 255) if mouse.dragging else (40, 220, 120),
                        2,
                        cv2.LINE_AA,
                    )
                    if shortcut_feedback is not None and monotonic() - shortcut_feedback[1] < 1.4:
                        cv2.putText(
                            frame,
                            shortcut_feedback[0],
                            (16, status_y + 28),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.65,
                            (40, 220, 120),
                            2,
                            cv2.LINE_AA,
                        )

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
    except pyautogui.FailSafeException as exc:
        raise RuntimeError(
            "Control detenido por el mecanismo de seguridad de PyAutoGUI "
            "al llegar a una esquina de la pantalla."
        ) from exc
    finally:
        if mouse is not None:
            mouse.close()
        capture.release()
        cv2.destroyAllWindows()
