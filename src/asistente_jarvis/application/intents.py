from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IntentKind(StrEnum):
    COPY = "copy"
    PASTE = "paste"
    SELECT_ALL = "select_all"
    SCREEN_SNIP = "screen_snip"
    RIGHT_CLICK = "right_click"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    SCROLL_VERTICAL = "scroll_vertical"
    SCROLL_HORIZONTAL = "scroll_horizontal"
    SWITCH_BEGIN = "switch_begin"
    SWITCH_NEXT = "switch_next"
    SWITCH_PREVIOUS = "switch_previous"
    SWITCH_END = "switch_end"
    UNDO = "undo"
    REDO = "redo"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    MEDIA_PLAY_PAUSE = "media_play_pause"
    MEDIA_PREVIOUS = "media_previous"
    MEDIA_NEXT = "media_next"


@dataclass(frozen=True, slots=True)
class Intent:
    """Una acción semántica todavía independiente de Windows y PyAutoGUI."""

    kind: IntentKind
    amount: int = 0


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Efectos visibles que la vista debe comunicar tras ejecutar una intención."""

    message: str | None = None
    overlay_message: str | None = None
    begin_snip: bool = False
