from __future__ import annotations

import ctypes
from ctypes import wintypes
from time import monotonic


class CommandOverlay:
    """Aviso pequeño de Windows que no recibe foco ni intercepta clics."""

    def __init__(self, duration_seconds: float = 1.6) -> None:
        self._user32 = ctypes.windll.user32
        self._gdi32 = ctypes.windll.gdi32
        self._duration = duration_seconds
        self._hide_at = float("-inf")

        self._user32.CreateWindowExW.restype = wintypes.HWND
        self._user32.CreateWindowExW.argtypes = (
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
        )
        self._user32.SetWindowPos.argtypes = (
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wintypes.UINT,
        )
        self._user32.PeekMessageW.argtypes = (
            ctypes.POINTER(wintypes.MSG), wintypes.HWND,
            wintypes.UINT, wintypes.UINT, wintypes.UINT,
        )
        self._user32.SendMessageW.argtypes = (
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
        )
        self._gdi32.GetStockObject.restype = wintypes.HANDLE

        width, height = 300, 48
        left = self._user32.GetSystemMetrics(0) - width - 24
        top = self._user32.GetSystemMetrics(1) - height - 64
        extended_style = 0x00000008 | 0x00000080 | 0x08000000 | 0x00000020 | 0x00080000
        style = 0x80000000 | 0x00800000 | 0x00000001 | 0x00000200
        self._window = self._user32.CreateWindowExW(
            extended_style, "STATIC", "", style,
            left, top, width, height, None, None, None, None,
        )
        if not self._window:
            raise RuntimeError("No fue posible crear el aviso de comandos de Windows.")
        self._user32.SetLayeredWindowAttributes(self._window, 0, 240, 0x00000002)
        font = self._gdi32.GetStockObject(17)
        if font:
            self._user32.SendMessageW(self._window, 0x0030, font, 1)

    def show(self, message: str) -> None:
        self._user32.SetWindowTextW(self._window, message)
        self._user32.SetWindowPos(
            self._window, wintypes.HWND(-1), 0, 0, 0, 0,
            0x0001 | 0x0002 | 0x0010 | 0x0040,
        )
        self._hide_at = monotonic() + self._duration
        self.update()

    def update(self) -> None:
        message = wintypes.MSG()
        while self._user32.PeekMessageW(ctypes.byref(message), self._window, 0, 0, 1):
            self._user32.TranslateMessage(ctypes.byref(message))
            self._user32.DispatchMessageW(ctypes.byref(message))
        if monotonic() >= self._hide_at:
            self._user32.ShowWindow(self._window, 0)

    def close(self) -> None:
        if self._window:
            self._user32.DestroyWindow(self._window)
            self._window = None
