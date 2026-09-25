from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from asistente_jarvis.config.cursor import (
    CursorCalibration, load_cursor_calibration, save_cursor_calibration,
)
from asistente_jarvis.controls.mouse import MouseController, MouseSettings
from asistente_jarvis.controls.overlay import CommandOverlay
from asistente_jarvis.controls.shortcuts import ShortcutController, ShortcutSettings
from asistente_jarvis.controls.two_hands import TwoHandController
from asistente_jarvis.controls.zoom import ZoomController
from asistente_jarvis.gestures.detector import (
    GESTURE_LABELS, Gesture, GestureResult, recognize_gesture,
)
from asistente_jarvis.gestures.geometry import NormalizedPoint, distance
from asistente_jarvis.vision.hand_tracker import HandObservation, HandTracker
from asistente_jarvis.vision.calibration import CalibrationPanel


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
    sensitivity: float | None = None
    select_all_mode: str = "auto"
    microphone: int | None = None
    speech_device: str = "auto"
    speech_language: str = "es"


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
    cv2: object,
    frame: object,
    observation: HandObservation,
    result: GestureResult,
    *,
    line: int = 0,
    display_gesture: Gesture | None = None,
) -> None:
    height, width = frame.shape[:2]
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

    shown = display_gesture or result.gesture
    label = (
        "PUNO / MODIFICADOR"
        if shown is Gesture.CLOSED_HAND and result.gesture is Gesture.PINCH
        else GESTURE_LABELS[shown]
    )
    title = f"{label}  |  {observation.handedness} {observation.confidence:.0%}"
    top = 12 + line * 44
    cv2.rectangle(frame, (12, top), (min(width - 12, 520), top + 43), (20, 20, 20), -1)
    cv2.putText(frame, title, (24, top + 31), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)


def _two_hand_gestures(
    results: list[GestureResult],
    observations: list[HandObservation],
    modifier_wrist: NormalizedPoint | None,
) -> tuple[Gesture, Gesture]:
    """Resuelve puño/pinza usando la otra mano y el modificador previo."""
    gestures = [result.gesture for result in results]
    if len(gestures) != 2:
        raise ValueError("Se esperan exactamente dos manos.")
    if Gesture.OPEN_PALM in gestures:
        return gestures[0], gestures[1]

    pinch_indexes = [
        index for index, result in enumerate(results)
        if result.gesture is Gesture.PINCH
    ]
    if len(pinch_indexes) == 2:
        return gestures[0], gestures[1]
    if modifier_wrist is not None and pinch_indexes:
        index = min(
            pinch_indexes,
            key=lambda item: distance(observations[item].landmarks[0], modifier_wrist),
        )
        gestures[index] = Gesture.CLOSED_HAND
    elif len(pinch_indexes) == 1:
        other = 1 - pinch_indexes[0]
        if gestures[other] in (
            Gesture.POINTING, Gesture.VICTORY,
            Gesture.THUMBS_LEFT, Gesture.THUMBS_RIGHT,
        ):
            gestures[pinch_indexes[0]] = Gesture.CLOSED_HAND
    return gestures[0], gestures[1]


def _draw_cursor_diagnostics(
    cv2: object, frame: object, mouse: MouseController, calibration: CursorCalibration
) -> None:
    height, width = frame.shape[:2]
    raw, filtered, target = mouse.cursor_diagnostics
    if raw is not None:
        cv2.circle(frame, _pixel(raw, width, height), 10, (0, 220, 255), 2, cv2.LINE_AA)
    if filtered is not None:
        cv2.circle(frame, _pixel(filtered, width, height), 5, (255, 255, 0), -1, cv2.LINE_AA)
    if raw is not None and filtered is not None:
        cv2.line(frame, _pixel(raw, width, height), _pixel(filtered, width, height),
                 (255, 255, 0), 1, cv2.LINE_AA)
    actual = mouse._current_position()
    lines = (
        f"CURSOR | sensibilidad {calibration.sensitivity:.2f}  "
        f"estabilidad {calibration.stability:.2f}  zona {calibration.deadzone_pixels:.1f}px",
        f"Bruto: {raw.x:.3f}, {raw.y:.3f}" if raw else "Bruto: --",
        f"Filtrado: {filtered.x:.3f}, {filtered.y:.3f}" if filtered else "Filtrado: --",
        f"Destino: {target[0]:.0f}, {target[1]:.0f} px | Real: "
        f"{actual[0]:.0f}, {actual[1]:.0f} px" if target else
        f"Destino: -- | Real: {actual[0]:.0f}, {actual[1]:.0f} px",
    )
    top = max(100, height - 151)
    cv2.rectangle(frame, (8, top), (min(width - 8, 565), top + 116), (20, 20, 20), -1)
    for index, line in enumerate(lines):
        cv2.putText(frame, line, (16, top + 23 + index * 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 235, 235), 1, cv2.LINE_AA)


def run_preview(options: PreviewOptions) -> int:
    import cv2
    import ctypes
    from ctypes import wintypes
    import pyautogui
    from asistente_jarvis.speech.dictation import DictationController
    from asistente_jarvis.speech.typing import DictationWriter, foreground_window
    from asistente_jarvis.config.paths import DEFAULT_WHISPER_MODEL_PATH

    calibration = load_cursor_calibration()
    if options.sensitivity is not None:
        calibration = CursorCalibration(
            sensitivity=options.sensitivity,
            stability=calibration.stability,
            deadzone_pixels=calibration.deadzone_pixels,
        )
    mouse = (
        MouseController(MouseSettings(
            sensitivity=calibration.sensitivity,
            stability=calibration.stability,
            jitter_pixels=calibration.deadzone_pixels,
        )) if options.control_mouse else None
    )
    shortcuts = (
        ShortcutController(ShortcutSettings(select_all_mode=options.select_all_mode))
        if options.control_mouse
        else None
    )
    zoom = ZoomController() if options.control_mouse else None
    two_hands = TwoHandController() if options.control_mouse else None
    dictation = (
        DictationController(
            DEFAULT_WHISPER_MODEL_PATH,
            microphone=options.microphone,
            device=options.speech_device,
            language=options.speech_language,
        ) if options.control_mouse else None
    )
    capture = _open_camera(cv2, options.camera_index, options.backend)
    overlay: CommandOverlay | None = None
    user32 = ctypes.windll.user32
    exit_hotkey_id = 0x4A52
    hotkey_registered = bool(user32.RegisterHotKey(None, exit_hotkey_id, 0x4002, 0x51))
    if not hotkey_registered:
        print("Aviso: Ctrl+Q ya está ocupado; se usará detección de teclas para salir.")
    f8_was_down = False
    f9_was_down = False
    f10_was_down = False
    calibration_panel: CalibrationPanel | None = None
    diagnostic_visible = False
    started_at = monotonic()
    last_frame_at = started_at
    fps = 0.0
    shortcut_feedback: tuple[str, float] | None = None
    waiting_for_pinch_release = False
    thumb_started: float | None = None
    thumb_pose: Gesture | None = None
    thumb_latched = False
    dictation_window = 0
    dictation_writer: DictationWriter | None = None
    stop_started: float | None = None
    stop_latched = False
    ctrl_q_was_down = False
    stop_hold_seconds = 2.0

    try:
        if mouse is not None:
            overlay = CommandOverlay()
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
                height, width = frame.shape[:2]
                results = [
                    recognize_gesture(observation.landmarks, aspect_ratio=width / height)
                    for observation in observations
                ]
                two_hand_gestures = (
                    _two_hand_gestures(
                        results,
                        observations,
                        two_hands.modifier_wrist if two_hands is not None else None,
                    )
                    if len(observations) == 2 else None
                )
                for index, observation in enumerate(observations):
                    _draw_hand(
                        cv2, frame, observation, results[index], line=index,
                        display_gesture=two_hand_gestures[index] if two_hand_gestures else None,
                    )

                if mouse is not None:
                    f9_is_down = bool(user32.GetAsyncKeyState(0x78) & 0x8000)
                    if f9_is_down and not f9_was_down:
                        if calibration_panel is None:
                            if dictation.busy:
                                if overlay is not None:
                                    overlay.show("Termina el dictado antes de calibrar")
                            else:
                                mouse.cancel_gesture()
                                shortcuts.reset()
                                zoom.reset()
                                two_hands.reset()
                                calibration_panel = CalibrationPanel(cv2, calibration)
                        else:
                            calibration = calibration_panel.values()
                            save_cursor_calibration(calibration)
                            calibration_panel.close()
                            calibration_panel = None
                            mouse.cancel_gesture()
                            if overlay is not None:
                                overlay.show("Calibracion guardada")
                    f9_was_down = f9_is_down
                    f10_is_down = bool(user32.GetAsyncKeyState(0x79) & 0x8000)
                    if f10_is_down and not f10_was_down:
                        diagnostic_visible = not diagnostic_visible
                    f10_was_down = f10_is_down
                    if calibration_panel is not None:
                        if calibration_panel.is_open():
                            updated = calibration_panel.values()
                            if updated != calibration:
                                calibration = updated
                                mouse.configure_cursor(calibration)
                            calibration_panel.show(calibration)
                        else:
                            save_cursor_calibration(calibration)
                            calibration_panel = None
                            mouse.cancel_gesture()
                    f8_is_down = bool(user32.GetAsyncKeyState(0x77) & 0x8000)
                    if f8_is_down and not f8_was_down:
                        if mouse.armed:
                            dictation.cancel()
                            dictation_writer = None
                            mouse.stop()
                        else:
                            mouse.arm()
                    f8_was_down = f8_is_down
                    action = None
                    for speech_event in dictation.poll():
                        event_action = None
                        if speech_event.kind == "text":
                            if speech_event.message:
                                try:
                                    if dictation_writer is None:
                                        raise RuntimeError("No hay un campo de texto asociado al dictado.")
                                    effects = dictation_writer.write(speech_event.message)
                                    event_action = (
                                        "Mensaje enviado" if "Enter" in effects
                                        else "Salto de línea" if "Shift+Enter" in effects
                                        else "Última palabra borrada" if "Borrar palabra" in effects
                                        else "Campo borrado" if "Borrar todo" in effects
                                        else "Dictado: texto escrito"
                                    )
                                except (RuntimeError, OSError) as exc:
                                    event_action = "Dictado no escrito; ver consola"
                                    print(f"Dictado: {speech_event.message}\nAviso: {exc}")
                        elif speech_event.kind == "error":
                            event_action = "Error de micrófono / Whisper"
                            print(f"Error de dictado: {speech_event.message}")
                        elif speech_event.kind in ("microphone", "backend"):
                            print(speech_event.message)
                        elif speech_event.kind == "fallback":
                            event_action = "CUDA no disponible: usando CPU"
                            print(speech_event.message)
                        elif speech_event.kind == "stopped":
                            event_action = "Tiempo máximo: terminando"
                        elif speech_event.kind == "done":
                            event_action = "Dictado terminado"
                            dictation_writer = None
                        if event_action is not None:
                            action = event_action
                            if overlay is not None:
                                overlay.show(event_action)
                    gesture = results[0].gesture if len(results) == 1 else None
                    now = monotonic()
                    if (gesture in (Gesture.THUMBS_UP, Gesture.THUMBS_DOWN)
                            and mouse.armed and calibration_panel is None):
                        if gesture is not thumb_pose:
                            thumb_pose = gesture
                            thumb_started = now
                            thumb_latched = False
                        if not thumb_latched:
                            if thumb_started is not None and now - thumb_started >= 0.6:
                                thumb_latched = True
                                if gesture is Gesture.THUMBS_UP and dictation.state == "idle":
                                    try:
                                        dictation_window = foreground_window()
                                        dictation.start()
                                        dictation_writer = DictationWriter(dictation_window)
                                        action = "Dictado: habla ahora"
                                        mouse.cancel_gesture()
                                        shortcuts.reset()
                                        zoom.reset()
                                        two_hands.reset()
                                    except (FileNotFoundError, RuntimeError) as exc:
                                        action = "Whisper no disponible"
                                        print(f"Error de dictado: {exc}")
                                elif gesture is Gesture.THUMBS_DOWN and dictation.state == "recording":
                                    dictation.finish()
                                    action = "Terminando dictado..."
                                if action and overlay is not None:
                                    overlay.show(action)
                    else:
                        thumb_pose = None
                        thumb_started = None
                        thumb_latched = False
                    stop_seen = (
                        calibration_panel is None
                        and any(result.gesture is Gesture.OPEN_PALM for result in results)
                    )
                    if stop_seen:
                        if stop_started is None:
                            stop_started = now
                        elif not stop_latched and now - stop_started >= stop_hold_seconds:
                            stop_latched = True
                            dictation.cancel()
                            dictation_writer = None
                            mouse.stop()
                            action = "STOP: control pausado"
                            if overlay is not None:
                                overlay.show(action)
                    else:
                        stop_started = None
                        stop_latched = False
                    if calibration_panel is not None:
                        shortcuts.reset()
                        zoom.reset()
                        two_hands.reset()
                        mouse.observe_cursor(
                            results[0].gesture if len(results) == 1 else None,
                            observations[0].landmarks if len(observations) == 1 else None,
                            now=now,
                        )
                    elif stop_seen:
                        # Durante la confirmación no se activa ningún otro gesto.
                        mouse.cancel_gesture()
                        shortcuts.reset()
                        zoom.reset()
                        two_hands.reset()
                    elif dictation.busy:
                        mouse.cancel_gesture()
                        shortcuts.reset()
                        zoom.reset()
                        two_hands.reset()
                    elif len(observations) == 2:
                        waiting_for_pinch_release = True
                        mouse.cancel_gesture()
                        shortcuts.reset()
                        gestures = two_hand_gestures
                        landmarks_pair = (observations[0].landmarks, observations[1].landmarks)
                        if any(
                            gesture in (Gesture.FIST, Gesture.CLOSED_HAND)
                            for gesture in gestures
                        ) or two_hands.mode == "switch":
                            if two_hands.mode == "switch":
                                zoom.reset()
                            else:
                                zoom.update(
                                    gestures,
                                    (landmarks_pair[0][8], landmarks_pair[1][8]),
                                    armed=mouse.armed,
                                )
                            action = two_hands.update(
                                gestures,
                                landmarks_pair,
                                armed=mouse.armed,
                            )
                        else:
                            two_hands.reset()
                            action = zoom.update(
                                gestures,
                                (landmarks_pair[0][8], landmarks_pair[1][8]),
                                armed=mouse.armed,
                            )
                    else:
                        zoom.reset()
                        two_hands.reset()
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
                        if action.startswith("Recorte"):
                            mouse.begin_snip()
                        if overlay is not None and (
                            action.startswith("Ctrl+")
                            or action.startswith("Recorte")
                            or action.startswith("Alt+Tab")
                            or action.startswith("Ventana")
                        ):
                            overlay.show(
                                "Recorte: señala, pinza y arrastra"
                                if action.startswith("Recorte")
                                else "Alt+Tab: inclina V a un lado"
                                if action.startswith("Alt+Tab")
                                else action
                            )

                    if calibration_panel is not None:
                        status = "CALIBRACION: AJUSTA CONTROLES; F9 GUARDA"
                    elif stop_seen and not stop_latched:
                        status = f"STOP: MANTEN PALMA {max(0, stop_hold_seconds - (now - stop_started)):.1f} S"
                    elif dictation.state == "recording":
                        status = "DICTANDO: PULGAR ABAJO PARA TERMINAR"
                    elif dictation.state == "finishing":
                        status = "PROCESANDO ULTIMOS FRAGMENTOS"
                    elif mouse.dragging:
                        status = "RECORTANDO" if mouse.snip_mode else "ARRASTRANDO"
                    elif not mouse.armed:
                        status = "PAUSADO"
                    elif mouse.snip_mode:
                        status = "RECORTE: INDICE, LUEGO PINZA"
                    elif len(observations) == 2:
                        if two_hands.mode == "switch":
                            side = "DER" if two_hands.switch_tilt >= 0 else "IZQ"
                            status = (
                                f"ALT+TAB: {side} {abs(two_hands.switch_tilt):.0f}"
                                "/14 GRADOS"
                            )
                        elif two_hands.mode == "scroll":
                            status = "SCROLL / INDICE + PUNO"
                        elif two_hands.mode == "thumb":
                            status = "DESHACER / REHACER"
                        elif two_hand_gestures == (Gesture.PINCH, Gesture.PINCH):
                            status = "ZOOM 2 MANOS"
                        else:
                            status = "2 MANOS"
                    elif results and results[0].gesture is Gesture.FIST:
                        status = "RECOLOCA LA MANO"
                    elif not results or results[0].gesture in (Gesture.UNKNOWN, Gesture.CLOSED_HAND):
                        status = "CURSOR QUIETO"
                    else:
                        status = "ACTIVO"
                    status_y = 82 + max(0, len(observations) - 1) * 44
                    cv2.putText(
                        frame,
                        f"{status} | F8 pausa | Ctrl+Q salir",
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
                    if diagnostic_visible or calibration_panel is not None:
                        _draw_cursor_diagnostics(cv2, frame, mouse, calibration)

                now = monotonic()
                if overlay is not None:
                    overlay.update()
                instant_fps = 1 / max(now - last_frame_at, 1e-6)
                fps = instant_fps if fps == 0 else fps * 0.9 + instant_fps * 0.1
                last_frame_at = now
                cv2.putText(
                    frame,
                    f"{fps:.0f} FPS | Ctrl+Q para salir",
                    (16, frame.shape[0] - 18),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (240, 240, 240),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("Asistente Jarvis - Reconocimiento preliminar", frame)
                hotkey_message = wintypes.MSG()
                if hotkey_registered:
                    while user32.PeekMessageW(
                        ctypes.byref(hotkey_message), wintypes.HWND(-1), 0x0312, 0x0312, 1
                    ):
                        if hotkey_message.wParam == exit_hotkey_id:
                            return 0
                ctrl_q_is_down = bool(
                    user32.GetAsyncKeyState(0x11) & 0x8000
                    and user32.GetAsyncKeyState(0x51) & 0x8000
                )
                if ctrl_q_is_down and not ctrl_q_was_down:
                    return 0
                ctrl_q_was_down = ctrl_q_is_down
                cv2.waitKey(1)
    except pyautogui.FailSafeException as exc:
        raise RuntimeError(
            "Control detenido por el mecanismo de seguridad de PyAutoGUI "
            "al llegar a una esquina de la pantalla."
        ) from exc
    finally:
        if calibration_panel is not None:
            save_cursor_calibration(calibration)
            calibration_panel.close()
        if hotkey_registered:
            user32.UnregisterHotKey(None, exit_hotkey_id)
        if overlay is not None:
            overlay.close()
        if two_hands is not None:
            two_hands.reset()
        if mouse is not None:
            mouse.close()
        if dictation is not None:
            dictation.close()
        capture.release()
        cv2.destroyAllWindows()
