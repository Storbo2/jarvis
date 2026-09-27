from __future__ import annotations

from asistente_jarvis.application.intents import Intent
from asistente_jarvis.controls.shortcuts import ShortcutController
from asistente_jarvis.controls.two_hands import TwoHandController
from asistente_jarvis.controls.zoom import ZoomController
from asistente_jarvis.gestures.detector import Gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint


class IntentResolver:
    """Coordina estados gestuales y produce intenciones sin controlar Windows."""

    def __init__(self) -> None:
        self.shortcuts = ShortcutController()
        self.two_hands = TwoHandController()
        self.zoom = ZoomController()

    @property
    def two_hand_mode(self) -> str | None:
        return self.two_hands.mode

    @property
    def modifier_wrist(self) -> NormalizedPoint | None:
        return self.two_hands.modifier_wrist

    @property
    def switch_tilt(self) -> float:
        return self.two_hands.switch_tilt

    @property
    def switch_threshold(self) -> float:
        return self.two_hands.settings.switch_tilt_degrees

    def reset_all(self) -> tuple[Intent, ...]:
        self.shortcuts.reset()
        self.zoom.reset()
        release = self.two_hands.reset()
        return (release,) if release is not None else ()

    def resolve_single_hand(
        self,
        gesture: Gesture | None,
        *,
        armed: bool,
        dragging: bool,
        now: float | None = None,
    ) -> tuple[Intent, ...]:
        self.zoom.reset()
        release = self.two_hands.reset()
        shortcut = self.shortcuts.update(
            gesture, armed=armed, dragging=dragging, now=now
        )
        return tuple(intent for intent in (release, shortcut) if intent is not None)

    def resolve_two_hands(
        self,
        gestures: tuple[Gesture, Gesture],
        landmarks: tuple[
            tuple[NormalizedPoint, ...], tuple[NormalizedPoint, ...]
        ],
        *,
        armed: bool,
        now: float | None = None,
    ) -> tuple[Intent, ...]:
        self.shortcuts.reset()
        if any(
            gesture in (Gesture.FIST, Gesture.CLOSED_HAND)
            for gesture in gestures
        ) or self.two_hands.mode == "switch":
            self.zoom.reset()
            intent = self.two_hands.update(
                gestures, landmarks, armed=armed, now=now
            )
            return (intent,) if intent is not None else ()

        release = self.two_hands.reset()
        zoom = self.zoom.update(
            gestures,
            (landmarks[0][8], landmarks[1][8]),
            armed=armed,
            now=now,
        )
        return tuple(intent for intent in (release, zoom) if intent is not None)
