from __future__ import annotations

import ctypes
from collections import deque
from dataclasses import dataclass
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint
from asistente_jarvis.controls.screen import set_cursor_position, virtual_desktop


@dataclass(frozen=True, slots=True)
class WindowSettings:
    grab_hold_seconds: float = 0.52
    drag_sensitivity: float = 1.25
    snap_hold_seconds: float = 0.35
    throw_edge: float = 0.12
    throw_distance: float = 0.24
    minimize_edge: float = 0.60
    minimize_distance: float = 0.14
    minimize_window_seconds: float = 0.42
    minimize_window_distance: float = 0.075
    minimize_velocity: float = 0.35


class WindowController:
    """Arrastra la ventana activa mediante su barra de título y aplica atajos Win."""

    def __init__(self, settings: WindowSettings | None = None) -> None:
        import pyautogui

        self.settings = settings or WindowSettings()
        self._input = pyautogui
        self._user32 = ctypes.windll.user32
        self._candidate_at: float | None = None
        self._grabbed = False
        self._window = 0
        self._hand_anchor: NormalizedPoint | None = None
        self._grab_wrist: NormalizedPoint | None = None
        self._mouse_anchor = (0, 0)
        self._motion_samples: deque[tuple[float, float]] = deque()
        self._snap_zone: str | None = None
        self._snap_candidate_at: float | None = None

    @property
    def grabbing(self) -> bool:
        return self._grabbed

    @property
    def candidate(self) -> bool:
        return self._candidate_at is not None

    @property
    def grab_wrist(self) -> NormalizedPoint | None:
        return self._grab_wrist

    def _begin(self, points: tuple[NormalizedPoint, ...], now: float) -> str | None:
        window = self._user32.GetForegroundWindow()
        if not window:
            return "No hay ventana activa"
        if self._user32.IsZoomed(window):
            self._user32.ShowWindow(window, 9)  # SW_RESTORE
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        rect = RECT()
        if not self._user32.GetWindowRect(window, ctypes.byref(rect)):
            return "No se pudo tomar la ventana"
        x = (rect.left + rect.right) // 2
        y = min(rect.bottom - 4, rect.top + 18)
        if not set_cursor_position(x, y):
            self._input.moveTo(x, y)
        self._input.mouseDown(button="left")
        self._window = window
        self._grabbed = True
        self._hand_anchor = points[9]
        self._grab_wrist = points[0]
        self._mouse_anchor = (x, y)
        self._motion_samples.clear()
        self._motion_samples.append((now, points[9].y))
        self._snap_zone = None
        self._snap_candidate_at = None
        return "Ventana tomada"

    def update(self, gesture: Gesture | None, points: tuple[NormalizedPoint, ...] | None, *, now: float | None = None) -> str | None:
        now = monotonic() if now is None else now
        if not self._grabbed:
            if gesture is not Gesture.WINDOW_GRAB or points is None:
                self._candidate_at = None
                return None
            if self._candidate_at is None:
                self._candidate_at = now
                return None
            if now - self._candidate_at >= self.settings.grab_hold_seconds:
                self._candidate_at = None
                return self._begin(points, now)
            return None
        if points is None:
            return self.cancel()
        if gesture is Gesture.OPEN_PALM:
            self._input.mouseUp(button="left")
            self._user32.ShowWindow(self._window, 3)  # SW_MAXIMIZE
            self._clear()
            return "Ventana maximizada"
        if gesture is Gesture.POINTING:
            self._input.mouseUp(button="left")
            self._clear()
            return "Ventana liberada; cursor activo"
        if gesture is None:
            return self.cancel()
        if self._hand_anchor is not None:
            desktop = virtual_desktop()
            width, height = desktop.width, desktop.height
            x = self._mouse_anchor[0] + (points[9].x - self._hand_anchor.x) * width * self.settings.drag_sensitivity
            y = self._mouse_anchor[1] + (points[9].y - self._hand_anchor.y) * height * self.settings.drag_sensitivity
            x, y = desktop.clamp(x, y)
            if not set_cursor_position(x, y):
                self._input.moveTo(x, y)
        self._grab_wrist = points[0]
        return self._try_throw(points, now)

    def _clear(self) -> None:
        self._candidate_at = None
        self._grabbed = False
        self._window = 0
        self._hand_anchor = None
        self._grab_wrist = None
        self._motion_samples.clear()
        self._snap_zone = None
        self._snap_candidate_at = None

    def cancel(self) -> str | None:
        if not self._grabbed:
            self._candidate_at = None
            return None
        self._input.mouseUp(button="left")
        self._clear()
        return "Ventana liberada"

    def snap(self, point: NormalizedPoint, *, now: float | None = None) -> str | None:
        if not self._grabbed:
            return None
        now = monotonic() if now is None else now
        horizontal = "left" if point.x < .38 else "right" if point.x > .62 else None
        if horizontal is None:
            self._snap_zone = None
            self._snap_candidate_at = None
            return None
        zone = horizontal
        if zone != self._snap_zone:
            self._snap_zone, self._snap_candidate_at = zone, now
            return None
        if self._snap_candidate_at is None or now - self._snap_candidate_at < self.settings.snap_hold_seconds:
            return None
        self._input.mouseUp(button="left")
        self._user32.SetForegroundWindow(self._window)
        self._input.hotkey("win", horizontal)
        label = "Mitad izquierda" if zone == "left" else "Mitad derecha"
        self._clear()
        return label

    def _try_throw(self, points: tuple[NormalizedPoint, ...], now: float) -> str | None:
        if self._hand_anchor is None:
            return None
        point = points[9]
        self._motion_samples.append((now, point.y))
        cutoff = now - self.settings.minimize_window_seconds
        while len(self._motion_samples) > 1 and self._motion_samples[0][0] < cutoff:
            self._motion_samples.popleft()
        oldest_at, oldest_y = self._motion_samples[0]
        elapsed = max(now - oldest_at, 1e-4)
        recent_drop = point.y - oldest_y
        downward_velocity = recent_drop / elapsed
        if (
            point.y > self.settings.minimize_edge
            and point.y - self._hand_anchor.y > self.settings.minimize_distance
            and recent_drop > self.settings.minimize_window_distance
            and downward_velocity > self.settings.minimize_velocity
        ):
            self._input.mouseUp(button="left")
            self._user32.ShowWindow(self._window, 6)  # SW_MINIMIZE
            self._clear()
            return "Ventana minimizada; cursor activo"
        if self._user32.GetSystemMetrics(80) < 2:
            return None
        delta = point.x - self._hand_anchor.x
        direction = "left" if point.x < self.settings.throw_edge and delta < -self.settings.throw_distance else "right" if point.x > 1 - self.settings.throw_edge and delta > self.settings.throw_distance else None
        if direction is None:
            return None
        self._input.mouseUp(button="left")
        self._user32.SetForegroundWindow(self._window)
        self._input.hotkey("win", "shift", direction)
        self._clear()
        return "Ventana enviada al monitor " + ("izquierdo" if direction == "left" else "derecho")

    def close(self) -> None:
        self.cancel()
