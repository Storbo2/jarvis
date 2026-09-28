from __future__ import annotations

import ctypes
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VirtualDesktop:
    """Geometría del escritorio virtual de Windows, incluidos monitores negativos."""

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width - 1

    @property
    def bottom(self) -> int:
        return self.top + self.height - 1

    def clamp(self, x: float, y: float) -> tuple[float, float]:
        return (
            max(float(self.left), min(float(self.right), x)),
            max(float(self.top), min(float(self.bottom), y)),
        )


def virtual_desktop() -> VirtualDesktop:
    user32 = ctypes.windll.user32
    # SM_X/YVIRTUALSCREEN, SM_CX/CYVIRTUALSCREEN.
    left = user32.GetSystemMetrics(76)
    top = user32.GetSystemMetrics(77)
    width = user32.GetSystemMetrics(78)
    height = user32.GetSystemMetrics(79)
    if width <= 0 or height <= 0:
        left = top = 0
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
    return VirtualDesktop(left, top, width, height)


def set_cursor_position(x: float, y: float) -> bool:
    return bool(ctypes.windll.user32.SetCursorPos(round(x), round(y)))
