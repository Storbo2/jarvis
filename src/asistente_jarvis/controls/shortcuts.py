from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture


@dataclass(frozen=True, slots=True)
class ShortcutSettings:
    hold_seconds: float = 0.45
    cooldown_seconds: float = 0.7


class ShortcutController:
    """Envía un atajo una sola vez por cada gesto sostenido."""

    def __init__(self, settings: ShortcutSettings | None = None) -> None:
        import pyautogui

        self._keyboard = pyautogui
        self.settings = settings or ShortcutSettings()
        self._candidate: Gesture | None = None
        self._candidate_since: float | None = None
        self._fired = False
        self._last_action_at = float("-inf")

    def reset(self) -> None:
        self._candidate = None
        self._candidate_since = None
        self._fired = False

    def update(
        self,
        gesture: Gesture | None,
        *,
        armed: bool,
        dragging: bool,
        now: float | None = None,
    ) -> str | None:
        now = monotonic() if now is None else now
        if not armed or dragging or gesture not in (Gesture.LETTER_C, Gesture.VICTORY):
            self.reset()
            return None

        if gesture is not self._candidate:
            self._candidate = gesture
            self._candidate_since = now
            self._fired = False
            return None

        if self._fired or self._candidate_since is None:
            return None
        if now - self._candidate_since < self.settings.hold_seconds:
            return None
        if now - self._last_action_at < self.settings.cooldown_seconds:
            return None

        key = "c" if gesture is Gesture.LETTER_C else "v"
        self._keyboard.hotkey("ctrl", key)
        self._fired = True
        self._last_action_at = now
        return "Ctrl+C enviado" if key == "c" else "Ctrl+V enviado"
