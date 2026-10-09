"""Acciones de voz deliberadamente limitadas y explícitas."""

from __future__ import annotations

import re
import unicodedata


def parse_open_app(transcript: str) -> str | None:
    """Acepta únicamente órdenes directas para abrir una aplicación."""
    normalized = unicodedata.normalize("NFKD", transcript.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
    words = normalized.split()
    while words and words[0] in {"hey", "jarvis", "por", "favor"}:
        words.pop(0)
    if not words or words[0] not in {"abre", "abrir", "inicia", "iniciar", "lanza", "lanzar"}:
        return None
    words.pop(0)
    if words and words[0] in {"la", "el", "app", "aplicacion", "programa"}:
        words.pop(0)
    app_name = " ".join(words).strip()
    if not app_name or len(app_name) > 60:
        return None
    return app_name


def open_start_app(app_name: str) -> None:
    """Abre la búsqueda de Inicio y escribe un nombre reconocido de aplicación."""
    import pyautogui

    pyautogui.press("win")
    pyautogui.sleep(0.35)
    pyautogui.write(app_name, interval=0.025)
    pyautogui.sleep(0.2)
    pyautogui.press("enter")
