from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint, distance


@dataclass(frozen=True, slots=True)
class ZoomSettings:
    hold_seconds: float = 0.35
    lost_pinch_grace_seconds: float = 0.12
    step_distance: float = 0.045
    min_interval_seconds: float = 0.15


class ZoomController:
    """Zoom por distancia entre dos pinzas, sin compartir estado con el mouse."""

    def __init__(self, settings: ZoomSettings | None = None) -> None:
        import pyautogui

        self._keyboard = pyautogui
        self.settings = settings or ZoomSettings()
        self._candidate_since: float | None = None
        self._missing_since: float | None = None
        self._reference_distance: float | None = None
        self._last_action_at = float("-inf")

    def reset(self) -> None:
        self._candidate_since = None
        self._missing_since = None
        self._reference_distance = None

    def update(
        self,
        gestures: tuple[Gesture, Gesture] | None,
        index_tips: tuple[NormalizedPoint, NormalizedPoint] | None,
        *,
        armed: bool,
        now: float | None = None,
    ) -> str | None:
        now = monotonic() if now is None else now
        if not armed or index_tips is None:
            self.reset()
            return None

        if gestures != (Gesture.PINCH, Gesture.PINCH):
            if self._candidate_since is not None:
                if self._missing_since is None:
                    self._missing_since = now
                if now - self._missing_since < self.settings.lost_pinch_grace_seconds:
                    return None
            self.reset()
            return None
        self._missing_since = None

        current_distance = distance(*index_tips)
        if self._candidate_since is None:
            self._candidate_since = now
            return None
        if now - self._candidate_since < self.settings.hold_seconds:
            return None
        if self._reference_distance is None:
            self._reference_distance = current_distance
            return None

        delta = current_distance - self._reference_distance
        if abs(delta) < self.settings.step_distance:
            return None
        if now - self._last_action_at < self.settings.min_interval_seconds:
            return None

        zoom_in = delta > 0
        self._keyboard.hotkey("ctrl", "add" if zoom_in else "subtract")
        self._reference_distance = current_distance
        self._last_action_at = now
        return "Zoom + enviado" if zoom_in else "Zoom - enviado"
