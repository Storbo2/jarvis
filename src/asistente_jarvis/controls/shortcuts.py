from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from asistente_jarvis.gestures.detector import Gesture


@dataclass(frozen=True, slots=True)
class ShortcutSettings:
    hold_seconds: float = 0.45
    cooldown_seconds: float = 0.7
    select_all_mode: str = "auto"


def _foreground_executable() -> str | None:
    """Obtiene el ejecutable de la ventana activa en Windows, si está disponible."""
    import ctypes
    from ctypes import wintypes
    from pathlib import PureWindowsPath

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
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

    def _select_all_key(self) -> str:
        mode = self.settings.select_all_mode
        if mode == "ctrl-a":
            return "a"
        if mode == "ctrl-e":
            return "e"
        return "e" if _foreground_executable() in {
            "explorer.exe",
            "winword.exe",
            "excel.exe",
            "powerpnt.exe",
        } else "a"

    def update(
        self,
        gesture: Gesture | None,
        *,
        armed: bool,
        dragging: bool,
        now: float | None = None,
    ) -> str | None:
        now = monotonic() if now is None else now
        if not armed or dragging or gesture not in (
            Gesture.LETTER_C,
            Gesture.VICTORY,
            Gesture.SELECT_ALL,
            Gesture.I_LOVE_YOU,
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
        if now - self._candidate_since < self.settings.hold_seconds:
            return None
        if now - self._last_action_at < self.settings.cooldown_seconds:
            return None

        if gesture is Gesture.I_LOVE_YOU:
            self._keyboard.hotkey("win", "shift", "s")
            self._fired = True
            self._last_action_at = now
            return "Recorte de pantalla activado"
        if gesture is Gesture.LETTER_C:
            key = "c"
        elif gesture is Gesture.VICTORY:
            key = "v"
        else:
            key = self._select_all_key()
        self._keyboard.hotkey("ctrl", key)
        self._fired = True
        self._last_action_at = now
        return f"Ctrl+{key.upper()} enviado"
