from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint


@dataclass(frozen=True, slots=True)
class MouseSettings:
    sensitivity: float = 0.8
    smoothing: float = 0.42
    jitter_pixels: float = 1.5
    drag_delay_seconds: float = 0.45
    pinch_release_grace_seconds: float = 0.1
    minimum_click_seconds: float = 0.08
    lost_hand_seconds: float = 0.35
    snip_timeout_seconds: float = 30.0


class MouseController:
    """Control del mouse con activación explícita y liberación garantizada."""

    def __init__(self, settings: MouseSettings | None = None) -> None:
        import pyautogui

        self._mouse = pyautogui
        self._mouse.FAILSAFE = True
        self._mouse.PAUSE = 0
        self.settings = settings or MouseSettings()
        if not 0.1 <= self.settings.sensitivity <= 4.0:
            raise ValueError("La sensibilidad debe estar entre 0.1 y 4.0.")
        self.width, self.height = self._mouse.size()
        self.armed = False
        self._pressed = False
        self._pinch_started: float | None = None
        self._pinch_lost_at: float | None = None
        self._last_seen: float | None = None
        self._last_position: tuple[float, float] | None = None
        self._target_position: tuple[float, float] | None = None
        self._pointing_anchor: NormalizedPoint | None = None
        self._pinch_anchor: NormalizedPoint | None = None
        self._pinch_screen_origin: tuple[float, float] | None = None
        self._snip_deadline: float | None = None
        self._snip_ready = False
        self._snip_dragging = False

    @property
    def dragging(self) -> bool:
        return self._pressed

    @property
    def snip_mode(self) -> bool:
        return self._snip_deadline is not None or self._snip_dragging

    def begin_snip(self) -> None:
        """La primera pinza tras abrir Recortes inicia un arrastre inmediato."""
        self._snip_deadline = monotonic() + self.settings.snip_timeout_seconds
        self._snip_ready = False
        self._snip_dragging = False

    def arm(self) -> None:
        self.armed = True
        self._clear_tracking()
        self._snip_deadline = None
        self._snip_ready = False
        self._snip_dragging = False
        self._last_seen = monotonic()

    def stop(self) -> None:
        self.armed = False
        self._clear_tracking()
        self._last_seen = None
        self._snip_deadline = None
        self._snip_ready = False
        self._release()

    def cancel_gesture(self) -> None:
        """Cancela clic/arrastre pendientes sin desarmar el control."""
        self._clear_tracking()
        self._snip_deadline = None
        self._snip_ready = False
        self._release()

    def _clear_tracking(self) -> None:
        self._pinch_started = None
        self._pinch_lost_at = None
        self._pinch_anchor = None
        self._pinch_screen_origin = None
        self._pointing_anchor = None
        self._target_position = None
        self._last_position = None

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
        self._snip_dragging = False

    def _current_position(self) -> tuple[float, float]:
        position = self._mouse.position()
        return float(position.x), float(position.y)

    def _screen_delta(self, before: NormalizedPoint, after: NormalizedPoint) -> tuple[float, float]:
        return (
            (after.x - before.x) * (self.width - 1) * self.settings.sensitivity,
            (after.y - before.y) * (self.height - 1) * self.settings.sensitivity,
        )

    @staticmethod
    def _pointing_position(landmarks: tuple[NormalizedPoint, ...]) -> NormalizedPoint:
        # La punta es expresiva pero tiembla; la articulación aporta estabilidad.
        tip = landmarks[8]
        joint = landmarks[6]
        return NormalizedPoint(
            tip.x * 0.65 + joint.x * 0.35,
            tip.y * 0.65 + joint.y * 0.35,
        )

    def _move_to(self, target: tuple[float, float]) -> None:
        old_x, old_y = self._last_position or self._current_position()
        target_x = max(0.0, min(self.width - 1, target[0]))
        target_y = max(0.0, min(self.height - 1, target[1]))
        remaining = hypot(target_x - old_x, target_y - old_y)
        if remaining < self.settings.jitter_pixels:
            return
        alpha = min(0.8, self.settings.smoothing + remaining / 400)
        x = old_x + alpha * (target_x - old_x)
        y = old_y + alpha * (target_y - old_y)
        self._mouse.moveTo(round(x), round(y), duration=0)
        self._last_position = (x, y)

    def update(
        self,
        gesture: Gesture | None,
        landmarks: tuple[NormalizedPoint, ...] | None,
        *,
        pinch_ratio: float | None = None,
        now: float | None = None,
    ) -> None:
        now = monotonic() if now is None else now
        if self._snip_deadline is not None and now >= self._snip_deadline:
            self._snip_deadline = None
            self._snip_ready = False

        if gesture is Gesture.OPEN_PALM:
            self.stop()
            return

        if landmarks is None:
            # Una sola imagen perdida cancela la pinza y libera un arrastre.
            self._clear_tracking()
            self._release()
            if self._last_seen is not None and now - self._last_seen >= self.settings.lost_hand_seconds:
                self.stop()
            return

        self._last_seen = now
        if not self.armed:
            return

        if (
            self._pinch_started is not None
            and gesture is not Gesture.FIST
            and pinch_ratio is not None
            and pinch_ratio <= 0.55
        ):
            gesture = Gesture.PINCH

        if gesture is Gesture.PINCH:
            self._pinch_lost_at = None
            if self._snip_deadline is not None and not self._snip_ready:
                return
            if self._pinch_started is None:
                self._pinch_started = now
                self._pinch_anchor = landmarks[9]
                self._pinch_screen_origin = self._current_position()
                self._last_position = self._pinch_screen_origin
                self._target_position = self._pinch_screen_origin
                self._pointing_anchor = None
                if self._snip_deadline is not None:
                    self._mouse.mouseDown(button="left")
                    self._pressed = True
                    self._snip_dragging = True
                    self._snip_deadline = None
                    self._snip_ready = False
            elif not self._pressed and now - self._pinch_started >= self.settings.drag_delay_seconds:
                self._mouse.mouseDown(button="left")
                self._pressed = True
                self._pinch_anchor = landmarks[9]
                self._pinch_screen_origin = self._current_position()
                return
            if self._pressed and self._pinch_anchor is not None and self._pinch_screen_origin is not None:
                dx, dy = self._screen_delta(self._pinch_anchor, landmarks[9])
                self._move_to((self._pinch_screen_origin[0] + dx, self._pinch_screen_origin[1] + dy))
            return

        if self._pinch_started is not None and gesture is not Gesture.FIST:
            if self._pinch_lost_at is None:
                self._pinch_lost_at = now
            if now - self._pinch_lost_at < self.settings.pinch_release_grace_seconds:
                return

        if gesture is Gesture.FIST and self._pinch_started is not None:
            # Al cerrar la mano para recolocarla, una pinza transitoria no debe hacer clic.
            self._release()
            self._pinch_started = None
            self._pinch_lost_at = None
            self._pinch_anchor = None
            self._pinch_screen_origin = None
            self._target_position = None
            self._pointing_anchor = None

        if self._pinch_started is not None:
            was_dragging = self._pressed
            pinch_duration = now - self._pinch_started
            self._release()
            self._pinch_started = None
            self._pinch_lost_at = None
            self._pinch_anchor = None
            self._pinch_screen_origin = None
            self._target_position = None
            self._pointing_anchor = None
            if not was_dragging and pinch_duration >= self.settings.minimum_click_seconds:
                self._mouse.click(button="left")

        if gesture is Gesture.POINTING:
            # Congela el cursor antes de que la pinza alcance el umbral del detector.
            if pinch_ratio is not None and pinch_ratio <= 0.7:
                self._pointing_anchor = None
                self._target_position = None
                return
            if self._snip_deadline is not None:
                self._snip_ready = True
            tip = self._pointing_position(landmarks)
            if self._pointing_anchor is None:
                self._pointing_anchor = tip
                self._target_position = self._current_position()
                self._last_position = self._target_position
            else:
                dx, dy = self._screen_delta(self._pointing_anchor, tip)
                target_x, target_y = self._target_position or self._current_position()
                self._target_position = (
                    max(0.0, min(self.width - 1, target_x + dx)),
                    max(0.0, min(self.height - 1, target_y + dy)),
                )
                self._pointing_anchor = tip
                self._move_to(self._target_position)
        else:
            self._pointing_anchor = None
            self._target_position = None

    def close(self) -> None:
        self.stop()
