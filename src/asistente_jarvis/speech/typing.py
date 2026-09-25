"""Inserción de texto Unicode en la ventana activa de Windows."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from asistente_jarvis.speech.commands import parse_dictation


class _KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("virtual_key", wintypes.WORD),
        ("scan_code", wintypes.WORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("extra_info", ctypes.c_size_t),
    ]


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG),
        ("mouse_data", wintypes.DWORD), ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("extra_info", ctypes.c_size_t),
    ]


class _HardwareInput(ctypes.Structure):
    _fields_ = [
        ("message", wintypes.DWORD), ("param_l", wintypes.WORD),
        ("param_h", wintypes.WORD),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [("keyboard", _KeyboardInput), ("mouse", _MouseInput), ("hardware", _HardwareInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("data", _InputUnion)]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_Input), ctypes.c_int)
_user32.SendInput.restype = wintypes.UINT


def foreground_window() -> int:
    return int(_user32.GetForegroundWindow() or 0)


def type_unicode(text: str, *, target_window: int) -> None:
    if not target_window or foreground_window() != target_window:
        raise RuntimeError("Cambió la ventana activa durante el dictado; texto no escrito.")
    encoded = text.encode("utf-16-le")
    units = [int.from_bytes(encoded[i:i + 2], "little") for i in range(0, len(encoded), 2)]
    for offset in range(0, len(units), 64):
        batch = units[offset:offset + 64]
        inputs = (_Input * (len(batch) * 2))()
        for index, unit in enumerate(batch):
            inputs[2 * index] = _Input(1, _InputUnion(keyboard=_KeyboardInput(0, unit, 0x0004, 0, 0)))
            inputs[2 * index + 1] = _Input(
                1, _InputUnion(keyboard=_KeyboardInput(0, unit, 0x0004 | 0x0002, 0, 0))
            )
        if foreground_window() != target_window:
            raise RuntimeError("Cambió la ventana activa durante la escritura.")
        sent = _user32.SendInput(len(inputs), inputs, ctypes.sizeof(_Input))
        if sent != len(inputs):
            raise OSError(ctypes.get_last_error(), "Windows no pudo escribir el texto transcrito.")


def _send_keys(*, target_window: int, strokes: list[tuple[int, int]]) -> None:
    if not target_window or foreground_window() != target_window:
        raise RuntimeError("Cambió la ventana activa durante el dictado; tecla no enviada.")
    inputs = (_Input * len(strokes))()
    for index, (key, flags) in enumerate(strokes):
        inputs[index] = _Input(1, _InputUnion(keyboard=_KeyboardInput(key, 0, flags, 0, 0)))
    sent = _user32.SendInput(len(inputs), inputs, ctypes.sizeof(_Input))
    if sent != len(inputs):
        raise OSError(ctypes.get_last_error(), "Windows no pudo enviar el atajo de dictado.")


def _enter(*, target_window: int, shift: bool) -> None:
    strokes = [(0x10, 0)] if shift else []
    strokes.extend(((0x0D, 0), (0x0D, 0x0002)))
    if shift:
        strokes.append((0x10, 0x0002))
    _send_keys(target_window=target_window, strokes=strokes)


def _delete_word(*, target_window: int) -> None:
    _send_keys(
        target_window=target_window,
        strokes=[(0x11, 0), (0x08, 0), (0x08, 0x0002), (0x11, 0x0002)],
    )


def _delete_all(*, target_window: int) -> None:
    _send_keys(
        target_window=target_window,
        strokes=[
            (0x11, 0), (0x41, 0), (0x41, 0x0002), (0x11, 0x0002),
            (0x08, 0), (0x08, 0x0002),
        ],
    )


class DictationWriter:
    """Conserva espacios entre fragmentos sin añadir signos de puntuación."""

    def __init__(self, target_window: int) -> None:
        self.target_window = target_window
        self._needs_space = False

    def write(self, transcript: str) -> list[str]:
        effects: list[str] = []
        for action in parse_dictation(transcript):
            if action.kind == "text":
                prefix = " " if self._needs_space else ""
                type_unicode(prefix + action.value, target_window=self.target_window)
                self._needs_space = True
                effects.append("text")
            elif action.kind == "punctuation":
                type_unicode(action.value, target_window=self.target_window)
                self._needs_space = True
                effects.append(action.value)
            elif action.kind == "newline":
                _enter(target_window=self.target_window, shift=True)
                self._needs_space = False
                effects.append("Shift+Enter")
            elif action.kind == "send":
                _enter(target_window=self.target_window, shift=False)
                self._needs_space = False
                effects.append("Enter")
            elif action.kind == "delete_word":
                _delete_word(target_window=self.target_window)
                self._needs_space = False
                effects.append("Borrar palabra")
            elif action.kind == "delete_all":
                _delete_all(target_window=self.target_window)
                self._needs_space = False
                effects.append("Borrar todo")
        return effects
