from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen


HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


def download_hand_landmarker(destination: Path, *, force: bool = False) -> Path:
    destination = destination.expanduser().resolve()
    if destination.exists() and not force:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    try:
        with urlopen(HAND_LANDMARKER_MODEL_URL, timeout=60) as response, partial.open("wb") as file:
            while chunk := response.read(1024 * 1024):
                file.write(chunk)
        if partial.stat().st_size < 1_000_000:
            raise RuntimeError("La descarga del modelo quedó incompleta.")
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)
    return destination
