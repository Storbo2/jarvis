from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from asistente_jarvis.gestures.geometry import NormalizedPoint


@dataclass(frozen=True, slots=True)
class HandObservation:
    landmarks: tuple[NormalizedPoint, ...]
    handedness: str
    confidence: float


class HandTracker:
    def __init__(
        self,
        model_path: Path,
        *,
        num_hands: int = 1,
        min_detection_confidence: float = 0.55,
        min_tracking_confidence: float = 0.55,
    ) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(
                f"No existe el modelo {model_path}. Ejecuta primero "
                "`uv run asistente-jarvis download-model`."
            )

        import mediapipe as mp

        self._mp = mp
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def detect(self, rgb_frame: object, timestamp_ms: int) -> list[HandObservation]:
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        observations: list[HandObservation] = []

        for index, raw_landmarks in enumerate(result.hand_landmarks):
            points = tuple(
                NormalizedPoint(point.x, point.y, point.z) for point in raw_landmarks
            )
            handedness = "Desconocida"
            confidence = 0.0
            if index < len(result.handedness) and result.handedness[index]:
                category = result.handedness[index][0]
                handedness = category.category_name or category.display_name or handedness
                confidence = float(category.score or 0.0)
            observations.append(HandObservation(points, handedness, confidence))
        return observations

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self) -> HandTracker:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
