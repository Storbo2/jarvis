from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from asistente_jarvis.application.intents import Intent, IntentKind
from asistente_jarvis.gestures.detector import Gesture


@dataclass(frozen=True, slots=True)
class ShortcutSettings:
    hold_seconds: float = 0.45
    right_click_hold_seconds: float = 0.32
    cooldown_seconds: float = 0.7
    select_all_mode: str = "auto"


class ShortcutController:
    """Confirma gestos sostenidos y emite una intención una sola vez."""

    def __init__(self, settings: ShortcutSettings | None = None) -> None:
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
    ) -> Intent | None:
        now = monotonic() if now is None else now
        if not armed or dragging or gesture not in (
            Gesture.LETTER_C,
            Gesture.VICTORY,
            Gesture.SELECT_ALL,
            Gesture.I_LOVE_YOU,
            Gesture.MIDDLE_PINCH,
        ):
            self.reset()
            return None

        if gesture is not self._candidate:
            self._candidate = gesture
            self._candidate_since = now
            self._fired = False
            return None

        if self._fired or self._candidate_since is None:
            return None
        hold_seconds = (
            self.settings.right_click_hold_seconds
            if gesture is Gesture.MIDDLE_PINCH
            else self.settings.hold_seconds
        )
        if now - self._candidate_since < hold_seconds:
            return None
        if now - self._last_action_at < self.settings.cooldown_seconds:
            return None

        if gesture is Gesture.I_LOVE_YOU:
            self._fired = True
            self._last_action_at = now
            return Intent(IntentKind.SCREEN_SNIP)
        if gesture is Gesture.MIDDLE_PINCH:
            self._fired = True
            self._last_action_at = now
            return Intent(IntentKind.RIGHT_CLICK)
        if gesture is Gesture.LETTER_C:
            kind = IntentKind.COPY
        elif gesture is Gesture.VICTORY:
            kind = IntentKind.PASTE
        else:
            kind = IntentKind.SELECT_ALL
        self._fired = True
        self._last_action_at = now
        return Intent(kind)
