"""Convierte palabras de dictado explícitas en texto y acciones."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class DictationAction:
    kind: str
    value: str = ""


_SPOKEN_COMMAND = re.compile(r"\b(dos\s+puntos|coma|punto|[eé]nter)\b", re.IGNORECASE)
_INFERRED_PUNCTUATION = re.compile(r"[.,:;!?¡¿]+")
_SPACES = re.compile(r"\s+")


def _command_key(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(character for character in normalized if unicodedata.category(character) != "Mn")


def parse_dictation(transcript: str) -> list[DictationAction]:
    """Ignora signos inferidos; solo las palabras de comando añaden puntuación.

    «Enviar» actúa si forma el fragmento completo o sigue una pausa marcada
    con puntuación, para limitar envíos accidentales.
    """
    literal = _SPACES.sub(" ", _INFERRED_PUNCTUATION.sub(" ", transcript)).strip()
    if not literal:
        return []
    command = _command_key(literal)
    if command in (
        "borrar palabra", "borra palabra", "borrar ultima palabra",
        "borrar la ultima palabra", "borra la ultima palabra",
    ):
        return [DictationAction("delete_word")]
    if command in ("borrar todo", "borra todo", "borrar todo el texto"):
        return [DictationAction("delete_all")]
    if command in ("enviar", "envia mensaje"):
        return [DictationAction("send")]
    # Una pausa que Whisper marca con puntuación puede quedar dentro del mismo
    # fragmento de audio. En ese caso conserva el texto previo y envía después.
    trailing_send = re.search(r"(?i)^(.+[,.;:!?])\s*enviar[.!?]?\s*$", transcript.strip())
    if trailing_send:
        return parse_dictation(trailing_send.group(1)) + [DictationAction("send")]

    actions: list[DictationAction] = []
    start = 0
    for match in _SPOKEN_COMMAND.finditer(literal):
        words = literal[start:match.start()].strip()
        if words:
            actions.append(DictationAction("text", words))
        command = _SPACES.sub(" ", match.group().casefold())
        if command == "coma":
            actions.append(DictationAction("punctuation", ","))
        elif command == "punto":
            actions.append(DictationAction("punctuation", "."))
        elif command == "dos puntos":
            actions.append(DictationAction("punctuation", ":"))
        else:
            actions.append(DictationAction("newline"))
        start = match.end()
    remaining = literal[start:].strip()
    if remaining:
        actions.append(DictationAction("text", remaining))
    return actions
