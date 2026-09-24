from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint


@dataclass(frozen=True, slots=True)
class MouseSettings:
    active_margin: float = 0.15
    smoothing: float = 0.25
    drag_delay_seconds: float = 0.45
    lost_hand_seconds: float = 0.35


class MouseController:
    """Control del mouse con activación explícita y liberación garantizada."""

    def __init__(self, settings: MouseSettings | None = None) -> None:
        import pyautogui

        self._mouse = pyautogui
        self._mouse.FAILSAFE = True
        self._mouse.PAUSE = 0
        self.settings = settings or MouseSettings()
        self.width, self.height = self._mouse.size()
        self.armed = False
        self._pressed = False
        self._pinch_started: float | None = None
        self._last_seen: float | None = None
        self._last_position: tuple[float, float] | None = None

    @property
    def dragging(self) -> bool:
        return self._pressed

    def arm(self) -> None:
        self.armed = True
        self._last_position = None
        self._pinch_started = None
        self._last_seen = monotonic()

    def stop(self) -> None:
        self.armed = False
        self._pinch_started = None
        self._last_position = None
        self._last_seen = None
        self._release()

    def _release(self) -> None:
        if self._pressed:
            self._pressed = False
            try:
                self._mouse.mouseUp(button="left")
            except self._mouse.FailSafeException:
                # El failsafe puede dispararse en una esquina durante un arrastre.
                # SendInput de botón arriba evita que quede presionado al salir.
                import ctypes

                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

    def _screen_position(self, point: NormalizedPoint) -> tuple[float, float]:
        margin = self.settings.active_margin
        span = 1 - 2 * margin
        x = max(0.0, min(1.0, (point.x - margin) / span))
        y = max(0.0, min(1.0, (point.y - margin) / span))
        return x * (self.width - 1), y * (self.height - 1)

    def _move(self, point: NormalizedPoint) -> None:
        target_x, target_y = self._screen_position(point)
        if self._last_position is None:
            x, y = target_x, target_y
        else:
            old_x, old_y = self._last_position
            alpha = self.settings.smoothing
            x = old_x + alpha * (target_x - old_x)
            y = old_y + alpha * (target_y - old_y)
        self._last_position = (x, y)
        self._mouse.moveTo(round(x), round(y), duration=0)

    def update(
        self,
        gesture: Gesture | None,
        landmarks: tuple[NormalizedPoint, ...] | None,
        *,
        now: float | None = None,
    ) -> None:
        now = monotonic() if now is None else now

        if gesture is Gesture.OPEN_PALM:
            self.stop()
            return

        if landmarks is None:
            # Una sola imagen perdida cancela la pinza y libera un arrastre.
            self._pinch_started = None
            self._release()
            if self._last_seen is not None and now - self._last_seen >= self.settings.lost_hand_seconds:
                self.stop()
            return

        self._last_seen = now
        if not self.armed:
            return

        if gesture is Gesture.PINCH:
            # El punto medio de la pinza reduce el salto entre señalar y arrastrar.
            anchor = NormalizedPoint(
                (landmarks[4].x + landmarks[8].x) / 2,
                (landmarks[4].y + landmarks[8].y) / 2,
            )
            self._move(anchor)
            if self._pinch_started is None:
                self._pinch_started = now
            elif not self._pressed and now - self._pinch_started >= self.settings.drag_delay_seconds:
                self._mouse.mouseDown(button="left")
                self._pressed = True
            return

        if self._pinch_started is not None:
            was_dragging = self._pressed
            self._release()
            self._pinch_started = None
            if not was_dragging:
                self._mouse.click(button="left")

        if gesture is Gesture.POINTING:
            self._move(landmarks[8])

    def close(self) -> None:
        self.stop()
