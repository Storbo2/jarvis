from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import hypot
from typing import Sequence

from asistente_jarvis.gestures.geometry import NormalizedPoint, distance, joint_angle


class Gesture(StrEnum):
    OPEN_PALM = "open_palm"
    PINCH = "pinch"
    POINTING = "pointing"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    THUMBS_LEFT = "thumbs_left"
    THUMBS_RIGHT = "thumbs_right"
    VICTORY = "victory"
    I_LOVE_YOU = "i_love_you"
    SELECT_ALL = "select_all"
    LETTER_C = "letter_c"
    FIST = "fist"
    CLOSED_HAND = "closed_hand"
    UNKNOWN = "unknown"


GESTURE_LABELS = {
    Gesture.OPEN_PALM: "STOP / PALMA ABIERTA",
    Gesture.PINCH: "PINZA",
    Gesture.POINTING: "INDICE",
    Gesture.THUMBS_UP: "PULGAR ARRIBA",
    Gesture.THUMBS_DOWN: "PULGAR ABAJO",
    Gesture.THUMBS_LEFT: "PULGAR IZQUIERDA",
    Gesture.THUMBS_RIGHT: "PULGAR DERECHA",
    Gesture.VICTORY: "V / DOS DEDOS",
    Gesture.I_LOVE_YOU: "ILOVEYOU / RECORTE",
    Gesture.SELECT_ALL: "A / V INVERTIDA",
    Gesture.LETTER_C: "C (EXPERIMENTAL)",
    Gesture.FIST: "PUNO FRONTAL / RECOLOCAR",
    Gesture.CLOSED_HAND: "MANO CERRADA",
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


def recognize_gesture(
    points: Sequence[NormalizedPoint], *, aspect_ratio: float = 1.0
) -> GestureResult:
    """Clasifica gestos simples usando proporciones independientes del tamaño de la mano."""

    if len(points) != 21:
        raise ValueError(f"Se esperaban 21 landmarks y se recibieron {len(points)}.")
    if aspect_ratio <= 0:
        raise ValueError("La proporción de la imagen debe ser positiva.")

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
    def camera_distance(first: NormalizedPoint, second: NormalizedPoint) -> float:
        return hypot(first.x - second.x, (first.y - second.y) / aspect_ratio)

    # El puño frontal acorta la palma proyectada y acerca los nudillos a la cámara.
    # En MediaPipe, un valor z menor indica un punto más cercano.
    palm_width = camera_distance(points[5], points[17])
    palm_length = camera_distance(points[0], points[9])
    knuckle_depth = points[0].z - (
        points[5].z + points[9].z + points[17].z
    ) / 3
    front_fist = (
        folded_others
        and not extended["thumb"]
        and palm_width > 1e-6
        and palm_length / palm_width < 1.05
        and knuckle_depth / palm_width > 0.28
    )
    if all(extended[name] for name in ("index", "middle", "ring", "pinky")):
        gesture = Gesture.OPEN_PALM
    elif front_fist:
        gesture = Gesture.FIST
    elif pinch_ratio <= 0.42:
        gesture = Gesture.PINCH
    elif (
        extended["thumb"]
        and not any(extended[name] for name in ("middle", "ring", "pinky"))
        and 0.58 <= pinch_ratio <= 1.65
        and 82 <= joint_angle(points[5], points[6], points[8]) < 155
        and distance(points[8], points[5]) / palm_scale >= 0.62
    ):
        # La C deja el índice curvado, pero separado de la palma. Evaluarla
        # antes del pulgar lateral evita que este último se quede con la pose.
        gesture = Gesture.LETTER_C
    elif (
        extended["thumb"]
        and folded_others
        and abs(points[4].x - points[2].x) / palm_scale >= 0.3
        and abs(points[4].x - points[2].x) > abs(points[4].y - points[2].y)
    ):
        gesture = Gesture.THUMBS_RIGHT if points[4].x > points[2].x else Gesture.THUMBS_LEFT
    elif (
        extended["thumb"]
        and folded_others
        and points[4].y < points[2].y - palm_scale * 0.35
    ):
        gesture = Gesture.THUMBS_UP
    elif (
        extended["thumb"]
        and folded_others
        and points[4].y > points[2].y + palm_scale * 0.35
    ):
        gesture = Gesture.THUMBS_DOWN
    elif (
        extended["thumb"]
        and extended["index"]
        and extended["pinky"]
        and not extended["middle"]
        and not extended["ring"]
    ):
        gesture = Gesture.I_LOVE_YOU
    elif (
        extended["index"]
        and extended["middle"]
        and not extended["ring"]
        and not extended["pinky"]
        and distance(points[8], points[12]) / palm_scale >= 0.4
    ):
        fingers_point_down = (
            points[8].y > points[5].y + palm_scale * 0.35
            and points[12].y > points[9].y + palm_scale * 0.35
        )
        gesture = Gesture.SELECT_ALL if fingers_point_down else Gesture.VICTORY
    elif extended["index"] and not any(
        extended[name] for name in ("middle", "ring", "pinky")
    ):
        gesture = Gesture.POINTING
    elif folded_others and not extended["thumb"]:
        gesture = Gesture.CLOSED_HAND
    else:
        gesture = Gesture.UNKNOWN

    return GestureResult(gesture, pinch_ratio, extended_names)
