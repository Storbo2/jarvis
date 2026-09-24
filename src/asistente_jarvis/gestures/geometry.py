from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, hypot


@dataclass(frozen=True, slots=True)
class NormalizedPoint:
    """Punto normalizado entregado por MediaPipe."""

    x: float
    y: float
    z: float = 0.0


def distance(a: NormalizedPoint, b: NormalizedPoint) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def joint_angle(a: NormalizedPoint, vertex: NormalizedPoint, c: NormalizedPoint) -> float:
    """Devuelve el ángulo a-vertex-c en grados."""

    first = (a.x - vertex.x, a.y - vertex.y)
    second = (c.x - vertex.x, c.y - vertex.y)
    first_length = hypot(*first)
    second_length = hypot(*second)
    if first_length == 0 or second_length == 0:
        return 0.0
    cosine = (first[0] * second[0] + first[1] * second[1]) / (
        first_length * second_length
    )
    return degrees(acos(max(-1.0, min(1.0, cosine))))
