from __future__ import annotations

import ctypes
from dataclasses import dataclass
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint


@dataclass(frozen=True, slots=True)
class TwoHandSettings:
    scroll_step: float = 0.045
    switch_step: float = 0.09
    switch_hold_seconds: float = 0.35
    switch_interval_seconds: float = 0.18


class TwoHandController:
    """Puño como modificador: índice para scroll o V para cambiar ventanas."""

    def __init__(self, settings: TwoHandSettings | None = None) -> None:
        import pyautogui

        self._keyboard = pyautogui
        self.settings = settings or TwoHandSettings()
        self._mode: str | None = None
        self._anchor: NormalizedPoint | None = None
        self._axis: str | None = None
        self._switch_candidate_at: float | None = None
        self._last_switch_at = float("-inf")
        self._alt_down = False

    @property
    def mode(self) -> str | None:
        return self._mode

    def reset(self) -> None:
        self._mode = None
        self._anchor = None
        self._axis = None
        self._switch_candidate_at = None
        if self._alt_down:
            self._release_key("alt", 0x12)
            self._alt_down = False

    def _release_key(self, key: str, virtual_key: int) -> None:
        try:
            self._keyboard.keyUp(key)
        except Exception:
            # Un fallo de automatización no debe dejar modificadores presionados.
            ctypes.windll.user32.keybd_event(virtual_key, 0, 0x0002, 0)

    @staticmethod
    def _wheel(axis: str, direction: int) -> None:
        event = 0x0800 if axis == "vertical" else 0x1000
        wheel_delta = (direction * 120) & 0xFFFFFFFF
        ctypes.windll.user32.mouse_event(event, 0, 0, ctypes.c_uint(wheel_delta), 0)

    def _scroll(self, tip: NormalizedPoint) -> str | None:
        if self._mode != "scroll" or self._anchor is None:
            self._mode = "scroll"
            self._anchor = tip
            self._axis = None
            return None

        dx = tip.x - self._anchor.x
        dy = tip.y - self._anchor.y
        if self._axis is None:
            if max(abs(dx), abs(dy)) < self.settings.scroll_step:
                return None
            self._axis = "horizontal" if abs(dx) > abs(dy) else "vertical"

        displacement = dx if self._axis == "horizontal" else dy
        if abs(displacement) < self.settings.scroll_step:
            return None
        direction = (1 if displacement > 0 else -1) if self._axis == "horizontal" else (-1 if displacement > 0 else 1)
        self._wheel(self._axis, direction)
        self._anchor = tip
        return "Scroll horizontal" if self._axis == "horizontal" else "Scroll vertical"

    def _switch(self, tip: NormalizedPoint, now: float) -> str | None:
        if self._mode != "switch":
            self._mode = "switch"
            self._switch_candidate_at = now
            self._anchor = tip
            return None

        if not self._alt_down:
            if self._switch_candidate_at is None or now - self._switch_candidate_at < self.settings.switch_hold_seconds:
                return None
            self._keyboard.keyDown("alt")
            self._alt_down = True
            self._keyboard.press("tab")
            self._last_switch_at = now
            self._anchor = tip
            return "Alt+Tab activo"

        if self._anchor is None:
            self._anchor = tip
            return None
        dx = tip.x - self._anchor.x
        if abs(dx) < self.settings.switch_step or now - self._last_switch_at < self.settings.switch_interval_seconds:
            return None
        if dx > 0:
            self._keyboard.press("tab")
            action = "Ventana siguiente"
        else:
            self._keyboard.keyDown("shift")
            try:
                self._keyboard.press("tab")
            finally:
                self._release_key("shift", 0x10)
            action = "Ventana anterior"
        self._last_switch_at = now
        self._anchor = tip
        return action

    def update(
        self,
        gestures: tuple[Gesture, Gesture] | None,
        landmarks: tuple[tuple[NormalizedPoint, ...], tuple[NormalizedPoint, ...]] | None,
        *,
        armed: bool,
        now: float | None = None,
    ) -> str | None:
        now = monotonic() if now is None else now
        if not armed or gestures is None or landmarks is None:
            self.reset()
            return None

        fist_indexes = [index for index, gesture in enumerate(gestures) if gesture is Gesture.FIST]
        if len(fist_indexes) != 1:
            self.reset()
            return None
        active_index = 1 - fist_indexes[0]
        active_gesture = gestures[active_index]
        active_points = landmarks[active_index]

        if self._alt_down:
            # Alt permanece presionado mientras el puño y ambas manos sigan visibles.
            if active_gesture is Gesture.VICTORY:
                midpoint = NormalizedPoint(
                    (active_points[8].x + active_points[12].x) / 2,
                    (active_points[8].y + active_points[12].y) / 2,
                )
                return self._switch(midpoint, now)
            self._anchor = None
            return None

        if active_gesture is Gesture.POINTING:
            return self._scroll(active_points[8])
        if active_gesture is Gesture.VICTORY:
            midpoint = NormalizedPoint(
                (active_points[8].x + active_points[12].x) / 2,
                (active_points[8].y + active_points[12].y) / 2,
            )
            return self._switch(midpoint, now)

        self.reset()
        return None
