from __future__ import annotations

import ctypes
from dataclasses import dataclass
from math import atan2, degrees
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint, distance


@dataclass(frozen=True, slots=True)
class TwoHandSettings:
    scroll_step: float = 0.045
    switch_hold_seconds: float = 0.35
    switch_tilt_degrees: float = 14.0
    switch_interval_seconds: float = 0.32
    thumb_hold_seconds: float = 0.45
    fist_grace_seconds: float = 0.2


class TwoHandController:
    """Puño como modificador: índice, V inclinada o pulgar lateral."""

    def __init__(self, settings: TwoHandSettings | None = None) -> None:
        import pyautogui

        self._keyboard = pyautogui
        self.settings = settings or TwoHandSettings()
        self._mode: str | None = None
        self._anchor: NormalizedPoint | None = None
        self._axis: str | None = None
        self._switch_candidate_at: float | None = None
        self._switch_neutral_angle: float | None = None
        self._last_switch_at = float("-inf")
        self._thumb_candidate: Gesture | None = None
        self._thumb_candidate_at: float | None = None
        self._thumb_fired = False
        self._alt_down = False
        self._current_tilt = 0.0
        self._fist_wrist: NormalizedPoint | None = None
        self._fist_last_seen_at: float | None = None

    @property
    def mode(self) -> str | None:
        return self._mode

    @property
    def switch_tilt(self) -> float:
        return self._current_tilt

    def reset(self) -> None:
        self._mode = None
        self._anchor = None
        self._axis = None
        self._switch_candidate_at = None
        self._switch_neutral_angle = None
        self._thumb_candidate = None
        self._thumb_candidate_at = None
        self._thumb_fired = False
        self._current_tilt = 0.0
        self._fist_wrist = None
        self._fist_last_seen_at = None
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

    @staticmethod
    def _wrist_angle(points: tuple[NormalizedPoint, ...]) -> float:
        wrist = points[0]
        palm_x = (points[5].x + points[17].x) / 2
        palm_y = (points[5].y + points[17].y) / 2
        return degrees(atan2(palm_y - wrist.y, palm_x - wrist.x))

    def _switch(self, points: tuple[NormalizedPoint, ...], now: float) -> str | None:
        angle = self._wrist_angle(points)
        if self._mode != "switch":
            self._mode = "switch"
            self._switch_candidate_at = now
            self._switch_neutral_angle = angle
            self._current_tilt = 0.0
            return None

        if not self._alt_down:
            if self._switch_candidate_at is None or now - self._switch_candidate_at < self.settings.switch_hold_seconds:
                return None
            self._keyboard.keyDown("alt")
            self._alt_down = True
            self._keyboard.press("tab")
            self._last_switch_at = now
            return "Alt+Tab activo"

        if self._switch_neutral_angle is None:
            self._switch_neutral_angle = angle
            return None
        tilt = (angle - self._switch_neutral_angle + 180) % 360 - 180
        self._current_tilt = tilt
        if abs(tilt) < self.settings.switch_tilt_degrees:
            self._last_switch_at = float("-inf")
            return None
        if now - self._last_switch_at < self.settings.switch_interval_seconds:
            return None
        if tilt > 0:
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
        return action

    def _thumb_shortcut(self, gesture: Gesture, now: float) -> str | None:
        if self._mode != "thumb" or self._thumb_candidate is not gesture:
            self._mode = "thumb"
            self._thumb_candidate = gesture
            self._thumb_candidate_at = now
            self._thumb_fired = False
            return None
        if self._thumb_fired or self._thumb_candidate_at is None:
            return None
        if now - self._thumb_candidate_at < self.settings.thumb_hold_seconds:
            return None
        key = "z" if gesture is Gesture.THUMBS_LEFT else "y"
        self._keyboard.hotkey("ctrl", key)
        self._thumb_fired = True
        return f"Ctrl+{key.upper()} enviado"

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

        fist_indexes = [
            index for index, gesture in enumerate(gestures)
            if gesture in (Gesture.FIST, Gesture.CLOSED_HAND)
        ]
        if len(fist_indexes) == 1:
            fist_index = fist_indexes[0]
            self._fist_wrist = landmarks[fist_index][0]
            self._fist_last_seen_at = now
        elif (
            self._alt_down
            and not fist_indexes
            and self._fist_wrist is not None
            and self._fist_last_seen_at is not None
            and now - self._fist_last_seen_at <= self.settings.fist_grace_seconds
        ):
            fist_index = min(
                range(2),
                key=lambda index: distance(landmarks[index][0], self._fist_wrist),
            )
        else:
            self.reset()
            return None
        active_index = 1 - fist_index
        active_gesture = gestures[active_index]
        active_points = landmarks[active_index]

        if self._alt_down:
            # Al inclinar la V su etiqueta puede fluctuar; el puño conserva Alt.
            if active_gesture not in (Gesture.THUMBS_LEFT, Gesture.THUMBS_RIGHT):
                return self._switch(active_points, now)
            self.reset()

        if active_gesture is Gesture.POINTING:
            return self._scroll(active_points[8])
        if active_gesture is Gesture.VICTORY:
            return self._switch(active_points, now)
        if active_gesture in (Gesture.THUMBS_LEFT, Gesture.THUMBS_RIGHT):
            return self._thumb_shortcut(active_gesture, now)

        self.reset()
        return None
