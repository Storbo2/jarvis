from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence

from asistente_jarvis.gestures.geometry import NormalizedPoint, distance, joint_angle


class Gesture(StrEnum):
    OPEN_PALM = "open_palm"
    PINCH = "pinch"
    POINTING = "pointing"
    THUMBS_UP = "thumbs_up"
    VICTORY = "victory"
    LETTER_C = "letter_c"
    UNKNOWN = "unknown"


GESTURE_LABELS = {
    Gesture.OPEN_PALM: "STOP / PALMA ABIERTA",
    Gesture.PINCH: "PINZA",
    Gesture.POINTING: "INDICE",
    Gesture.THUMBS_UP: "PULGAR ARRIBA",
    Gesture.VICTORY: "V / DOS DEDOS",
    Gesture.LETTER_C: "C (EXPERIMENTAL)",
    Gesture.UNKNOWN: "NEUTRO",
}


@dataclass(frozen=True, slots=True)
class GestureResult:
    gesture: Gesture
    pinch_ratio: float
    extended_fingers: tuple[str, ...]

    @property
    def label(self) -> str:
        return GESTURE_LABELS[self.gesture]


_FINGER_JOINTS = {
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}


def _finger_is_extended(points: Sequence[NormalizedPoint], joints: tuple[int, int, int]) -> bool:
    mcp, pip, tip = (points[index] for index in joints)
    wrist = points[0]
    return joint_angle(mcp, pip, tip) >= 155 and distance(tip, wrist) > distance(pip, wrist)


def recognize_gesture(points: Sequence[NormalizedPoint]) -> GestureResult:
    """Clasifica gestos simples usando proporciones independientes del tamaño de la mano."""

    if len(points) != 21:
        raise ValueError(f"Se esperaban 21 landmarks y se recibieron {len(points)}.")

    palm_scale = distance(points[0], points[9])
    if palm_scale < 1e-6:
        return GestureResult(Gesture.UNKNOWN, float("inf"), ())

    extended = {
        name: _finger_is_extended(points, joints) for name, joints in _FINGER_JOINTS.items()
    }
    thumb_angle = joint_angle(points[2], points[3], points[4])
    extended["thumb"] = (
        thumb_angle >= 145 and distance(points[4], points[5]) / palm_scale >= 0.6
    )
    extended_names = tuple(name for name, is_extended in extended.items() if is_extended)
    pinch_ratio = distance(points[4], points[8]) / palm_scale

    folded_others = not any(extended[name] for name in ("index", "middle", "ring", "pinky"))
    if all(extended.values()):
        gesture = Gesture.OPEN_PALM
    elif pinch_ratio <= 0.42:
        gesture = Gesture.PINCH
    elif (
        extended["thumb"]
        and folded_others
        and points[4].y < points[2].y - palm_scale * 0.35
    ):
        gesture = Gesture.THUMBS_UP
    elif (
        extended["index"]
        and extended["middle"]
        and not extended["ring"]
        and not extended["pinky"]
        and distance(points[8], points[12]) / palm_scale >= 0.4
    ):
        gesture = Gesture.VICTORY
    elif extended["index"] and not any(
        extended[name] for name in ("middle", "ring", "pinky")
    ):
        gesture = Gesture.POINTING
    elif (
        extended["thumb"]
        and not extended["middle"]
        and not extended["ring"]
        and not extended["pinky"]
        and 0.65 <= pinch_ratio <= 1.5
        and 90 <= joint_angle(points[5], points[6], points[8]) < 155
    ):
        gesture = Gesture.LETTER_C
    else:
        gesture = Gesture.UNKNOWN

    return GestureResult(gesture, pinch_ratio, extended_names)
