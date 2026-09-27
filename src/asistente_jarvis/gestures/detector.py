from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import hypot
from typing import Sequence

from asistente_jarvis.gestures.geometry import NormalizedPoint, distance, joint_angle


INDEX_PINCH_THRESHOLD = 0.50
MIDDLE_PINCH_THRESHOLD = 0.38


class Gesture(StrEnum):
    OPEN_PALM = "open_palm"
    PINCH = "pinch"
    MIDDLE_PINCH = "middle_pinch"
    POINTING = "pointing"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    THUMBS_LEFT = "thumbs_left"
    THUMBS_RIGHT = "thumbs_right"
    VICTORY = "victory"
    PINCH_PREPARATION = "pinch_preparation"
    I_LOVE_YOU = "i_love_you"
    ROCK = "rock"
    WINDOW_GRAB = "window_grab"
    SELECT_ALL = "select_all"
    LETTER_C = "letter_c"
    FIST = "fist"
    CLOSED_HAND = "closed_hand"
    UNKNOWN = "unknown"


GESTURE_LABELS = {
    Gesture.OPEN_PALM: "PALMA ABIERTA",
    Gesture.PINCH: "PINZA",
    Gesture.MIDDLE_PINCH: "PINZA MEDIA / CLIC DERECHO",
    Gesture.POINTING: "INDICE",
    Gesture.THUMBS_UP: "PULGAR ARRIBA",
    Gesture.THUMBS_DOWN: "PULGAR ABAJO",
    Gesture.THUMBS_LEFT: "PULGAR IZQUIERDA",
    Gesture.THUMBS_RIGHT: "PULGAR DERECHA",
    Gesture.VICTORY: "V / DOS DEDOS",
    Gesture.PINCH_PREPARATION: "PREPARANDO PINZA",
    Gesture.I_LOVE_YOU: "ILOVEYOU / RECORTE",
    Gesture.ROCK: "CUERNOS",
    Gesture.WINDOW_GRAB: "GARRA / TOMAR VENTANA",
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
    middle_pinch_ratio: float = float("inf")
    middle_pinch_ready: bool = False

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
    thumb_away_from_palm = distance(points[4], points[5]) / palm_scale >= 0.58
    extended["thumb"] = (
        thumb_angle >= 145 and thumb_away_from_palm
    )
    extended_names = tuple(name for name, is_extended in extended.items() if is_extended)
    pinch_ratio = distance(points[4], points[8]) / palm_scale
    middle_pinch_ratio = distance(points[4], points[12]) / palm_scale
    middle_tip_reach = distance(points[12], points[9]) / palm_scale
    middle_tip_outward = distance(points[12], points[0]) / max(
        distance(points[10], points[0]), 1e-6
    )
    middle_depth_delta = abs(points[4].z - points[12].z) / palm_scale
    middle_pinch_ready = (
        extended["index"]
        and middle_tip_reach >= 0.68
        and middle_tip_outward >= 0.92
        and joint_angle(points[9], points[10], points[12]) >= 90
        and middle_depth_delta <= 0.35
    )

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
    fingertip_indexes = (4, 8, 12, 16, 20)
    tip_center_x = sum(points[index].x for index in fingertip_indexes) / len(fingertip_indexes)
    tip_center_y = sum(points[index].y for index in fingertip_indexes) / len(fingertip_indexes)
    tip_spread = max(
        hypot(points[index].x - tip_center_x, points[index].y - tip_center_y)
        for index in fingertip_indexes
    ) / palm_scale
    fingertips_forward = sum(points[index].z for index in fingertip_indexes) / len(fingertip_indexes)
    knuckles_depth = sum(points[index].z for index in (5, 9, 13, 17)) / 4
    window_grab = (
        folded_others
        and not extended["thumb"]
        and not front_fist
        and tip_spread <= 0.92
        and fingertips_forward < knuckles_depth - palm_scale * 0.10
    )
    if front_fist:
        gesture = Gesture.FIST
    elif window_grab:
        gesture = Gesture.WINDOW_GRAB
    elif (
        middle_pinch_ratio <= MIDDLE_PINCH_THRESHOLD
        and pinch_ratio >= 0.58
        and middle_pinch_ready
    ):
        # El índice permanece separado y apuntando: así la pinza pulgar-medio
        # no compite con la pinza pulgar-índice usada para clic y arrastre.
        gesture = Gesture.MIDDLE_PINCH
    elif pinch_ratio <= INDEX_PINCH_THRESHOLD:
        gesture = Gesture.PINCH
    elif all(extended[name] for name in ("index", "middle", "ring", "pinky")):
        # Las pinzas tienen prioridad cuando las puntas ya se tocaron. Esto
        # permite mantener los otros dedos levantados sin convertir el clic
        # en una palma abierta transitoria.
        gesture = Gesture.OPEN_PALM
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
        and extended["pinky"]
        and not extended["middle"]
        and not extended["ring"]
    ):
        gesture = Gesture.ROCK
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
        gesture = (
            Gesture.SELECT_ALL
            if fingers_point_down
            else Gesture.PINCH_PREPARATION
            if thumb_away_from_palm
            else Gesture.VICTORY
        )
    elif extended["index"] and not any(
        extended[name] for name in ("middle", "ring", "pinky")
    ):
        gesture = Gesture.POINTING
    elif folded_others and not extended["thumb"]:
        gesture = Gesture.CLOSED_HAND
    else:
        gesture = Gesture.UNKNOWN

    return GestureResult(
        gesture, pinch_ratio, extended_names,
        middle_pinch_ratio=middle_pinch_ratio,
        middle_pinch_ready=middle_pinch_ready,
    )
