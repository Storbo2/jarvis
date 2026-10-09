from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from asistente_jarvis.application.dispatcher import ActionDispatcher
from asistente_jarvis.application.intents import ActionResult, Intent
from asistente_jarvis.application.resolver import IntentResolver
from asistente_jarvis.config.cursor import (
    CursorCalibration, load_cursor_calibration, save_cursor_calibration,
)
from asistente_jarvis.controls.mouse import MouseController, MouseSettings
from asistente_jarvis.controls.overlay import CommandOverlay
from asistente_jarvis.controls.window import WindowController
from asistente_jarvis.gestures.detector import (
    GESTURE_LABELS,
    INDEX_PINCH_THRESHOLD,
    MIDDLE_PINCH_THRESHOLD,
    Gesture,
    GestureResult,
    recognize_gesture,
)
from asistente_jarvis.gestures.geometry import NormalizedPoint, distance
from asistente_jarvis.vision.hand_tracker import HandObservation, HandTracker
from asistente_jarvis.vision.calibration import CalibrationPanel
from asistente_jarvis.speech.voice_assistant import VoiceAssistantController


HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)

WINDOW_TITLE = "JARVIS // VISION LINK"
HUD_CYAN = (255, 225, 40)
HUD_ORANGE = (40, 110, 255)
HUD_DARK = (12, 22, 30)


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
    voice_assistant: bool = True


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


def _draw_hud_frame(cv2: object, frame: object, *, armed: bool) -> None:
    height, width = frame.shape[:2]
    color = HUD_CYAN if armed else HUD_ORANGE
    cv2.rectangle(frame, (0, 0), (width - 1, 31), HUD_DARK, -1)
    cv2.line(frame, (0, 32), (width, 32), color, 1, cv2.LINE_AA)
    cv2.putText(
        frame, "J.A.R.V.I.S  //  VISION LINK", (14, 22),
        cv2.FONT_HERSHEY_DUPLEX, 0.55, color, 1, cv2.LINE_AA,
    )
    state = "ONLINE" if armed else "STANDBY"
    state_width = cv2.getTextSize(state, cv2.FONT_HERSHEY_DUPLEX, 0.48, 1)[0][0]
    cv2.putText(
        frame, state, (width - state_width - 14, 22),
        cv2.FONT_HERSHEY_DUPLEX, 0.48, color, 1, cv2.LINE_AA,
    )
    corner = 20
    for x, y, sx, sy in (
        (5, 38, 1, 1), (width - 6, 38, -1, 1),
        (5, height - 6, 1, -1), (width - 6, height - 6, -1, -1),
    ):
        cv2.line(frame, (x, y), (x + sx * corner, y), color, 1, cv2.LINE_AA)
        cv2.line(frame, (x, y), (x, y + sy * corner), color, 1, cv2.LINE_AA)


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
    color = (40, 110, 255) if result.gesture is Gesture.OPEN_PALM else (255, 225, 40)

    for start, end in HAND_CONNECTIONS:
        cv2.line(
            frame,
            _pixel(observation.landmarks[start], width, height),
            _pixel(observation.landmarks[end], width, height),
            (120, 185, 205),
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
    top = 42 + line * 42
    cv2.rectangle(frame, (12, top), (min(width - 12, 520), top + 39), (12, 22, 30), -1)
    cv2.rectangle(frame, (12, top), (min(width - 12, 520), top + 39), color, 1)
    cv2.putText(frame, title, (24, top + 27), cv2.FONT_HERSHEY_DUPLEX, 0.58, color, 1, cv2.LINE_AA)


def _two_hand_gestures(
    results: list[GestureResult],
    observations: list[HandObservation],
    modifier_wrist: NormalizedPoint | None,
) -> tuple[Gesture, Gesture]:
    """Resuelve puño/pinza usando la otra mano y el modificador previo."""
    gestures = [result.gesture for result in results]
    if len(gestures) != 2:
        raise ValueError("Se esperan exactamente dos manos.")
    grab_indexes = [
        index for index, gesture in enumerate(gestures)
        if gesture is Gesture.WINDOW_GRAB
    ]
    if len(grab_indexes) == 1:
        other = 1 - grab_indexes[0]
        if gestures[other] in (
            Gesture.POINTING, Gesture.VICTORY, Gesture.PINCH_PREPARATION,
            Gesture.THUMBS_LEFT, Gesture.THUMBS_RIGHT, Gesture.THUMBS_UP,
            Gesture.THUMBS_DOWN, Gesture.OPEN_PALM, Gesture.I_LOVE_YOU, Gesture.ROCK,
        ):
            gestures[grab_indexes[0]] = Gesture.CLOSED_HAND

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
            Gesture.POINTING, Gesture.VICTORY, Gesture.PINCH_PREPARATION,
            Gesture.THUMBS_LEFT, Gesture.THUMBS_RIGHT, Gesture.THUMBS_UP,
            Gesture.THUMBS_DOWN, Gesture.OPEN_PALM, Gesture.I_LOVE_YOU, Gesture.ROCK,
        ):
            gestures[pinch_indexes[0]] = Gesture.CLOSED_HAND
    return gestures[0], gestures[1]


def _draw_cursor_diagnostics(
    cv2: object,
    frame: object,
    mouse: MouseController,
    calibration: CursorCalibration,
    gesture_result: GestureResult | None,
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
        (
            f"Pinza indice: {gesture_result.pinch_ratio:.2f}/{INDEX_PINCH_THRESHOLD:.2f} | "
            f"medio: {gesture_result.middle_pinch_ratio:.2f}/{MIDDLE_PINCH_THRESHOLD:.2f} | "
            f"listo: {'SI' if gesture_result.middle_pinch_ready else 'NO'}"
            if gesture_result is not None else "Pinzas: --"
        ),
        f"Destino: {target[0]:.0f}, {target[1]:.0f} px | Real: "
        f"{actual[0]:.0f}, {actual[1]:.0f} px" if target else
        f"Destino: -- | Real: {actual[0]:.0f}, {actual[1]:.0f} px",
    )
    top = max(100, height - 179)
    cv2.rectangle(frame, (8, top), (min(width - 8, 565), top + 144), (20, 20, 20), -1)
    for index, line in enumerate(lines):
        cv2.putText(frame, line, (16, top + 23 + index * 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 235, 235), 1, cv2.LINE_AA)


def _dispatch_intents(
    dispatcher: ActionDispatcher, intents: tuple[Intent, ...]
) -> ActionResult:
    combined = ActionResult()
    for intent in intents:
        current = dispatcher.dispatch(intent)
        combined = ActionResult(
            message=current.message or combined.message,
            overlay_message=current.overlay_message or combined.overlay_message,
            begin_snip=current.begin_snip or combined.begin_snip,
        )
    return combined


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
    resolver = IntentResolver() if options.control_mouse else None
    dispatcher = (
        ActionDispatcher(select_all_mode=options.select_all_mode)
        if options.control_mouse else None
    )
    window = WindowController() if options.control_mouse else None
    dictation = (
        DictationController(
            DEFAULT_WHISPER_MODEL_PATH,
            microphone=options.microphone,
            device=options.speech_device,
            language=options.speech_language,
        ) if options.control_mouse else None
    )
    voice_assistant = (
        VoiceAssistantController(dictation)
        if options.control_mouse and options.voice_assistant else None
    )
    capture = _open_camera(cv2, options.camera_index, options.backend)
    overlay: CommandOverlay | None = None
    user32 = ctypes.windll.user32
    preview_width, preview_height = 480, 360
    screen_width = user32.GetSystemMetrics(0)
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, preview_width, preview_height)
    cv2.moveWindow(
        WINDOW_TITLE,
        max(24, screen_width - preview_width - 120),
        64,
    )
    topmost_property = getattr(cv2, "WND_PROP_TOPMOST", None)
    if topmost_property is not None:
        try:
            cv2.setWindowProperty(WINDOW_TITLE, topmost_property, 1)
        except cv2.error:
            print("Aviso: OpenCV no pudo mantener la cámara siempre visible.")
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
        if voice_assistant is not None:
            voice_assistant.start()
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
                _draw_hud_frame(
                    cv2, frame, armed=mouse is None or mouse.armed
                )
                two_hand_gestures = (
                    _two_hand_gestures(
                        results,
                        observations,
                        resolver.modifier_wrist if resolver is not None else None,
                    )
                    if len(observations) == 2 else None
                )
                for index, observation in enumerate(observations):
                    _draw_hand(
                        cv2, frame, observation, results[index], line=index,
                        display_gesture=two_hand_gestures[index] if two_hand_gestures else None,
                    )

                if mouse is not None:
                    assert resolver is not None and dispatcher is not None
                    f9_is_down = bool(user32.GetAsyncKeyState(0x78) & 0x8000)
                    if f9_is_down and not f9_was_down:
                        if calibration_panel is None:
                            if dictation.busy:
                                if overlay is not None:
                                    overlay.show("Termina el dictado antes de calibrar")
                            else:
                                mouse.cancel_gesture()
                                window.cancel()
                                _dispatch_intents(dispatcher, resolver.reset_all())
                                calibration_panel = CalibrationPanel(cv2, calibration)
                        else:
                            calibration = calibration_panel.values()
                            save_cursor_calibration(calibration)
                            calibration_panel.close()
                            calibration_panel = None
                            mouse.cancel_gesture()
                            window.cancel()
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
                            window.cancel()
                    f8_is_down = bool(user32.GetAsyncKeyState(0x77) & 0x8000)
                    if f8_is_down and not f8_was_down:
                        if mouse.armed:
                            dictation.cancel()
                            dictation_writer = None
                            if voice_assistant is not None:
                                voice_assistant.resume()
                            mouse.stop()
                            window.cancel()
                            _dispatch_intents(dispatcher, resolver.reset_all())
                        else:
                            mouse.arm()
                    f8_was_down = f8_is_down
                    action = None
                    gesture_result = ActionResult()
                    if voice_assistant is not None:
                        for voice_event in voice_assistant.poll():
                            if voice_event.kind == "microphone":
                                print(voice_event.message)
                            elif voice_event.kind == "transcript":
                                print(f"Hey Jarvis oyó: {voice_event.message}")
                            elif voice_event.kind == "error":
                                print(f"Asistente de voz: {voice_event.message}")
                                action = "Asistente de voz no disponible"
                            elif voice_event.kind in ("action", "ignored", "wake"):
                                action = voice_event.message or "Hey Jarvis: escuchando orden"
                            if voice_event.kind in ("wake", "action", "ignored", "error"):
                                if overlay is not None and action is not None:
                                    overlay.show(action)
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
                            if voice_assistant is not None:
                                voice_assistant.resume()
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
                            if voice_assistant is not None:
                                voice_assistant.resume()
                        if event_action is not None:
                            action = event_action
                            if overlay is not None:
                                overlay.show(event_action)
                    gesture = results[0].gesture if len(results) == 1 else None
                    now = monotonic()
                    both_palms = (
                        len(results) == 2
                        and all(
                            result.gesture is Gesture.OPEN_PALM
                            for result in results
                        )
                    )
                    window_hand_index: int | None = None
                    if both_palms and window.grabbing:
                        action = window.cancel()
                    elif window.grabbing and not observations:
                        action = window.cancel()
                    elif window.grabbing and observations and window.grab_wrist is not None:
                        window_hand_index = min(
                            range(len(observations)),
                            key=lambda index: distance(
                                observations[index].landmarks[0], window.grab_wrist
                            ),
                        )
                    elif not window.grabbing and len(observations) == 1:
                        grabs = [
                            index for index, result in enumerate(results)
                            if result.gesture is Gesture.WINDOW_GRAB
                        ]
                        if grabs:
                            window_hand_index = grabs[0]
                        elif window.candidate:
                            window.update(None, None, now=now)
                    elif window.candidate:
                        # Una segunda mano o un cambio de pose invalida la
                        # confirmación: la garra debe sostenerse de continuo.
                        window.update(None, None, now=now)
                    handling_window = window_hand_index is not None or action == "Ventana liberada"
                    if window_hand_index is not None:
                        mouse.cancel_gesture()
                        _dispatch_intents(dispatcher, resolver.reset_all())
                        window_action = window.update(
                            results[window_hand_index].gesture,
                            observations[window_hand_index].landmarks,
                            now=now,
                        )
                        if window.grabbing and len(observations) == 2:
                            other_index = 1 - window_hand_index
                            if results[other_index].gesture is Gesture.POINTING:
                                snap_action = window.snap(
                                    observations[other_index].landmarks[8], now=now
                                )
                                window_action = snap_action or window_action
                        if window_action is not None:
                            action = window_action
                            if overlay is not None:
                                overlay.show(window_action)
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
                                        if voice_assistant is not None and not voice_assistant.pause():
                                            raise RuntimeError("Jarvis aún está procesando una orden de voz.")
                                        dictation_window = foreground_window()
                                        dictation.start()
                                        dictation_writer = DictationWriter(dictation_window)
                                        action = "Dictado: habla ahora"
                                        mouse.cancel_gesture()
                                        _dispatch_intents(dispatcher, resolver.reset_all())
                                    except (FileNotFoundError, RuntimeError) as exc:
                                        if voice_assistant is not None:
                                            voice_assistant.resume()
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
                        and both_palms
                    )
                    if stop_seen:
                        if stop_started is None:
                            stop_started = now
                        elif not stop_latched and now - stop_started >= stop_hold_seconds:
                            stop_latched = True
                            dictation.cancel()
                            dictation_writer = None
                            if voice_assistant is not None:
                                voice_assistant.resume()
                            mouse.stop()
                            action = "STOP: control pausado"
                            if overlay is not None:
                                overlay.show(action)
                    else:
                        stop_started = None
                        stop_latched = False
                    if calibration_panel is not None:
                        _dispatch_intents(dispatcher, resolver.reset_all())
                        mouse.observe_cursor(
                            results[0].gesture if len(results) == 1 else None,
                            observations[0].landmarks if len(observations) == 1 else None,
                            now=now,
                        )
                    elif stop_seen:
                        # Durante la confirmación no se activa ningún otro gesto.
                        mouse.cancel_gesture()
                        _dispatch_intents(dispatcher, resolver.reset_all())
                    elif dictation.busy:
                        mouse.cancel_gesture()
                        _dispatch_intents(dispatcher, resolver.reset_all())
                    elif handling_window:
                        mouse.cancel_gesture()
                        _dispatch_intents(dispatcher, resolver.reset_all())
                    elif len(observations) == 2:
                        waiting_for_pinch_release = True
                        mouse.cancel_gesture()
                        gestures = two_hand_gestures
                        landmarks_pair = (observations[0].landmarks, observations[1].landmarks)
                        gesture_result = _dispatch_intents(
                            dispatcher,
                            resolver.resolve_two_hands(
                                gestures,
                                landmarks_pair,
                                armed=mouse.armed,
                                now=now,
                            ),
                        )
                        if gesture_result.message is not None:
                            action = gesture_result.message
                    else:
                        gesture = results[0].gesture if results else None
                        landmarks = observations[0].landmarks if observations else None
                        pinch_ratio = results[0].pinch_ratio if results else None
                        if waiting_for_pinch_release and gesture is Gesture.PINCH:
                            mouse.cancel_gesture()
                            gesture_result = _dispatch_intents(
                                dispatcher, resolver.reset_all()
                            )
                        else:
                            if gesture is not None:
                                waiting_for_pinch_release = False
                            mouse.update(gesture, landmarks, pinch_ratio=pinch_ratio)
                            gesture_result = _dispatch_intents(
                                dispatcher,
                                resolver.resolve_single_hand(
                                    gesture,
                                    armed=mouse.armed,
                                    dragging=mouse.dragging or mouse.snip_mode,
                                    now=now,
                                ),
                            )
                        if gesture_result.message is not None:
                            action = gesture_result.message
                    if gesture_result.begin_snip:
                        mouse.begin_snip()
                    if gesture_result.overlay_message and overlay is not None:
                        overlay.show(gesture_result.overlay_message)
                    if not mouse.armed:
                        shortcut_feedback = None
                    if action is not None:
                        shortcut_feedback = (action, monotonic())

                    if calibration_panel is not None:
                        status = "CALIBRACION: AJUSTA CONTROLES; F9 GUARDA"
                    elif stop_seen and not stop_latched:
                        status = f"STOP: MANTEN AMBAS PALMAS {max(0, stop_hold_seconds - (now - stop_started)):.1f} S"
                    elif dictation.state == "recording":
                        status = "DICTANDO: PULGAR ABAJO PARA TERMINAR"
                    elif dictation.state == "finishing":
                        status = "PROCESANDO ULTIMOS FRAGMENTOS"
                    elif voice_assistant is not None and voice_assistant.state == "command":
                        status = "HEY JARVIS: ESCUCHANDO ORDEN"
                    elif voice_assistant is not None and voice_assistant.state == "processing":
                        status = "PROCESANDO ORDEN DE VOZ"
                    elif voice_assistant is not None and voice_assistant.state == "wake":
                        status = "HEY JARVIS: ESCUCHA LOCAL ACTIVA"
                    elif window.grabbing:
                        status = "VENTANA TOMADA: ABRE LA MANO PARA MAXIMIZAR"
                    elif window.candidate:
                        status = "TOMAR VENTANA: MANTEN LA GARRA"
                    elif mouse.dragging:
                        status = "RECORTANDO" if mouse.snip_mode else "ARRASTRANDO"
                    elif not mouse.armed:
                        status = "PAUSADO"
                    elif mouse.snip_mode:
                        status = "RECORTE: INDICE, LUEGO PINZA"
                    elif len(observations) == 2:
                        if resolver.two_hand_mode == "switch":
                            tilt = resolver.switch_tilt
                            side = (
                                "CENTRO"
                                if abs(tilt) < resolver.switch_threshold
                                else "DER" if tilt > 0 else "IZQ"
                            )
                            status = (
                                f"ALT+TAB: {side} {abs(tilt):.0f}"
                                f"/{resolver.switch_threshold:.0f} GRADOS"
                            )
                        elif resolver.two_hand_mode == "scroll":
                            status = "SCROLL / INDICE + PUNO"
                        elif resolver.two_hand_mode == "thumb":
                            status = "DESHACER / REHACER"
                        elif resolver.two_hand_mode == "media":
                            status = "MULTIMEDIA / PUNO + GESTO"
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
                    status_y = 84 + max(0, len(observations) - 1) * 42
                    cv2.putText(
                        frame,
                        f"{status} | F8 pausa | Ctrl+Q salir",
                        (16, status_y),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.48,
                        HUD_ORANGE if mouse.dragging else HUD_CYAN,
                        1,
                        cv2.LINE_AA,
                    )
                    if shortcut_feedback is not None and monotonic() - shortcut_feedback[1] < 1.4:
                        cv2.putText(
                            frame,
                            shortcut_feedback[0],
                            (16, status_y + 28),
                            cv2.FONT_HERSHEY_DUPLEX,
                            0.56,
                            HUD_CYAN,
                            1,
                            cv2.LINE_AA,
                        )
                    if diagnostic_visible or calibration_panel is not None:
                        _draw_cursor_diagnostics(
                            cv2,
                            frame,
                            mouse,
                            calibration,
                            results[0] if len(results) == 1 else None,
                        )

                now = monotonic()
                if overlay is not None:
                    overlay.update()
                instant_fps = 1 / max(now - last_frame_at, 1e-6)
                fps = instant_fps if fps == 0 else fps * 0.9 + instant_fps * 0.1
                last_frame_at = now
                cv2.putText(
                    frame,
                    f"SYS {fps:.0f} FPS  //  CTRL+Q EXIT",
                    (16, frame.shape[0] - 18),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.45,
                    HUD_CYAN,
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow(WINDOW_TITLE, frame)
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
        if resolver is not None and dispatcher is not None:
            _dispatch_intents(dispatcher, resolver.reset_all())
            dispatcher.close()
        if window is not None:
            window.close()
        if mouse is not None:
            mouse.close()
        if voice_assistant is not None:
            voice_assistant.close()
        if dictation is not None:
            dictation.close()
        capture.release()
        cv2.destroyAllWindows()
