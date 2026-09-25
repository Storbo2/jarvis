from __future__ import annotations

from asistente_jarvis.config.cursor import CursorCalibration


class CalibrationPanel:
    """Controles de OpenCV para afinar el cursor sin activar acciones gestuales."""

    TITLE = "Jarvis - Calibracion del cursor"

    def __init__(self, cv2: object, calibration: CursorCalibration) -> None:
        self.cv2 = cv2
        self.cv2.namedWindow(self.TITLE, self.cv2.WINDOW_NORMAL)
        self.cv2.resizeWindow(self.TITLE, 590, 270)
        self.cv2.createTrackbar(
            "Sensibilidad x100", self.TITLE, round(calibration.sensitivity * 100), 400, lambda _: None
        )
        self.cv2.createTrackbar(
            "Estabilidad %", self.TITLE, round(calibration.stability * 100), 100, lambda _: None
        )
        self.cv2.createTrackbar(
            "Zona muerta x10", self.TITLE, round(calibration.deadzone_pixels * 10), 100,
            lambda _: None,
        )

    def is_open(self) -> bool:
        try:
            return self.cv2.getWindowProperty(self.TITLE, self.cv2.WND_PROP_VISIBLE) >= 1
        except self.cv2.error:
            return False

    def values(self) -> CursorCalibration:
        return CursorCalibration(
            sensitivity=max(10, self.cv2.getTrackbarPos("Sensibilidad x100", self.TITLE)) / 100,
            stability=self.cv2.getTrackbarPos("Estabilidad %", self.TITLE) / 100,
            deadzone_pixels=self.cv2.getTrackbarPos("Zona muerta x10", self.TITLE) / 10,
        )

    def show(self, calibration: CursorCalibration) -> None:
        import numpy as np

        canvas = np.full((140, 590, 3), (30, 34, 39), dtype=np.uint8)
        lines = (
            "F9 o cerrar ventana: guardar y volver",
            "Mientras este panel esta abierto, los gestos no ejecutan acciones.",
            f"Sensibilidad {calibration.sensitivity:.2f}  |  "
            f"Estabilidad {calibration.stability:.2f}  |  "
            f"Zona muerta {calibration.deadzone_pixels:.1f} px",
            "F10: mostrar u ocultar diagnostico en la camara",
        )
        for index, line in enumerate(lines):
            self.cv2.putText(
                canvas, line, (12, 27 + 30 * index), self.cv2.FONT_HERSHEY_SIMPLEX,
                0.52, (225, 235, 240), 1, self.cv2.LINE_AA,
            )
        self.cv2.imshow(self.TITLE, canvas)

    def close(self) -> None:
        if self.is_open():
            self.cv2.destroyWindow(self.TITLE)
