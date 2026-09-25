from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from asistente_jarvis.config.paths import PROJECT_ROOT


CALIBRATION_PATH = PROJECT_ROOT / "data" / "cursor_calibration.json"


@dataclass(frozen=True, slots=True)
class CursorCalibration:
    sensitivity: float = 0.8
    stability: float = 0.5
    deadzone_pixels: float = 1.5

    def __post_init__(self) -> None:
        if not 0.1 <= self.sensitivity <= 4.0:
            raise ValueError("La sensibilidad debe estar entre 0.1 y 4.0.")
        if not 0.0 <= self.stability <= 1.0:
            raise ValueError("La estabilidad debe estar entre 0 y 1.")
        if not 0.0 <= self.deadzone_pixels <= 10.0:
            raise ValueError("La zona muerta debe estar entre 0 y 10 px.")


def load_cursor_calibration(path: Path = CALIBRATION_PATH) -> CursorCalibration:
    if not path.exists():
        return CursorCalibration()
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
        return CursorCalibration(**values)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Aviso: calibración local inválida ({exc}); usando valores iniciales.")
        return CursorCalibration()


def save_cursor_calibration(
    calibration: CursorCalibration, path: Path = CALIBRATION_PATH
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(asdict(calibration), indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
