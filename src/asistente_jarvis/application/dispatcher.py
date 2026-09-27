from __future__ import annotations

import ctypes
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import PureWindowsPath

from asistente_jarvis.application.intents import ActionResult, Intent, IntentKind


@dataclass(frozen=True, slots=True)
class ActionRecord:
    occurred_at: datetime
    intent: Intent
    message: str | None


def _foreground_executable() -> str | None:
    """Obtiene el ejecutable de la ventana activa en Windows, si está disponible."""
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (
        wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
    )
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = (
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
    )
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    window = user32.GetForegroundWindow()
    if not window:
        return None
    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(window, ctypes.byref(process_id))
    if not process_id.value:
        return None
    process = kernel32.OpenProcess(0x1000, False, process_id.value)
    if not process:
        return None
    try:
        path = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(path))
        if kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)):
            return PureWindowsPath(path.value).name.lower()
    finally:
        kernel32.CloseHandle(process)
    return None


class ActionDispatcher:
    """Único punto de salida para atajos, rueda y modificadores de Windows."""

    def __init__(self, *, select_all_mode: str = "auto", history_size: int = 50) -> None:
        import pyautogui

        if select_all_mode not in {"auto", "ctrl-a", "ctrl-e"}:
            raise ValueError(f"Modo de selección desconocido: {select_all_mode}")
        self._input = pyautogui
        self._select_all_mode = select_all_mode
        self._alt_down = False
        self._history: deque[ActionRecord] = deque(maxlen=history_size)

    @property
    def history(self) -> tuple[ActionRecord, ...]:
        return tuple(self._history)

    def _release_key(self, key: str, virtual_key: int) -> None:
        try:
            self._input.keyUp(key)
        except Exception:
            ctypes.windll.user32.keybd_event(virtual_key, 0, 0x0002, 0)

    def _select_all_key(self) -> str:
        if self._select_all_mode == "ctrl-a":
            return "a"
        if self._select_all_mode == "ctrl-e":
            return "e"
        return "e" if _foreground_executable() in {
            "explorer.exe",
            "winword.exe",
            "excel.exe",
            "powerpnt.exe",
        } else "a"

    @staticmethod
    def _wheel(axis: str, direction: int) -> None:
        event = 0x0800 if axis == "vertical" else 0x1000
        wheel_delta = (direction * 120) & 0xFFFFFFFF
        ctypes.windll.user32.mouse_event(
            event, 0, 0, ctypes.c_uint(wheel_delta), 0
        )

    def dispatch(self, intent: Intent) -> ActionResult:
        result = self._execute(intent)
        self._history.append(ActionRecord(datetime.now(), intent, result.message))
        return result

    def _execute(self, intent: Intent) -> ActionResult:
        kind = intent.kind
        if kind is IntentKind.COPY:
            self._input.hotkey("ctrl", "c")
            return ActionResult("Ctrl+C enviado", "Ctrl+C enviado")
        if kind is IntentKind.PASTE:
            self._input.hotkey("ctrl", "v")
            return ActionResult("Ctrl+V enviado", "Ctrl+V enviado")
        if kind is IntentKind.SELECT_ALL:
            key = self._select_all_key()
            self._input.hotkey("ctrl", key)
            message = f"Ctrl+{key.upper()} enviado"
            return ActionResult(message, message)
        if kind is IntentKind.SCREEN_SNIP:
            self._input.hotkey("win", "shift", "s")
            return ActionResult(
                "Recorte de pantalla activado",
                "Recorte: señala, pinza y arrastra",
                begin_snip=True,
            )
        if kind is IntentKind.RIGHT_CLICK:
            self._input.click(button="right")
            return ActionResult("Clic derecho", "Clic derecho")
        if kind in (IntentKind.ZOOM_IN, IntentKind.ZOOM_OUT):
            zoom_in = kind is IntentKind.ZOOM_IN
            self._input.hotkey("ctrl", "add" if zoom_in else "subtract")
            return ActionResult("Zoom + enviado" if zoom_in else "Zoom - enviado")
        if kind in (IntentKind.SCROLL_VERTICAL, IntentKind.SCROLL_HORIZONTAL):
            axis = "vertical" if kind is IntentKind.SCROLL_VERTICAL else "horizontal"
            self._wheel(axis, intent.amount)
            return ActionResult(
                "Scroll vertical" if axis == "vertical" else "Scroll horizontal"
            )
        if kind is IntentKind.SWITCH_BEGIN:
            if not self._alt_down:
                self._input.keyDown("alt")
                self._alt_down = True
            self._input.press("tab")
            return ActionResult("Alt+Tab activo", "Alt+Tab: inclina V a un lado")
        if kind is IntentKind.SWITCH_NEXT:
            self._input.press("tab")
            return ActionResult("Ventana siguiente", "Ventana siguiente")
        if kind is IntentKind.SWITCH_PREVIOUS:
            self._input.keyDown("shift")
            try:
                self._input.press("tab")
            finally:
                self._release_key("shift", 0x10)
            return ActionResult("Ventana anterior", "Ventana anterior")
        if kind is IntentKind.SWITCH_END:
            if self._alt_down:
                self._release_key("alt", 0x12)
                self._alt_down = False
            return ActionResult()
        if kind in (IntentKind.UNDO, IntentKind.REDO):
            key = "z" if kind is IntentKind.UNDO else "y"
            self._input.hotkey("ctrl", key)
            message = f"Ctrl+{key.upper()} enviado"
            return ActionResult(message, message)
        if kind in (IntentKind.VOLUME_UP, IntentKind.VOLUME_DOWN):
            up = kind is IntentKind.VOLUME_UP
            self._input.press("volumeup" if up else "volumedown")
            message = "Volumen +" if up else "Volumen -"
            return ActionResult(message, message)
        if kind is IntentKind.MEDIA_PLAY_PAUSE:
            self._input.press("playpause")
            return ActionResult("Reproducir / pausar", "Reproducir / pausar")
        if kind in (IntentKind.MEDIA_PREVIOUS, IntentKind.MEDIA_NEXT):
            previous = kind is IntentKind.MEDIA_PREVIOUS
            self._input.press("prevtrack" if previous else "nexttrack")
            message = "Pista anterior" if previous else "Pista siguiente"
            return ActionResult(message, message)
        raise ValueError(f"Intención desconocida: {kind}")

    def close(self) -> None:
        if self._alt_down:
            self._release_key("alt", 0x12)
            self._alt_down = False
