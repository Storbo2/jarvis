from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees
from time import monotonic

from asistente_jarvis.application.intents import Intent, IntentKind
from asistente_jarvis.gestures.detector import Gesture
from asistente_jarvis.gestures.geometry import NormalizedPoint, distance


@dataclass(frozen=True, slots=True)
class TwoHandSettings:
    scroll_step: float = 0.045
    switch_hold_seconds: float = 0.28
    switch_tilt_degrees: float = 10.0
    switch_repeat_delay_seconds: float = 0.38
    switch_slow_interval_seconds: float = 0.28
    switch_fast_interval_seconds: float = 0.12
    switch_full_speed_degrees: float = 34.0
    thumb_hold_seconds: float = 0.45
    media_hold_seconds: float = 0.38
    volume_repeat_seconds: float = 0.22
    fist_grace_seconds: float = 0.3


class TwoHandController:
    """Puño como modificador: índice, V inclinada o pulgar lateral."""

    def __init__(self, settings: TwoHandSettings | None = None) -> None:
        self.settings = settings or TwoHandSettings()
        self._mode: str | None = None
        self._anchor: NormalizedPoint | None = None
        self._axis: str | None = None
        self._switch_candidate_at: float | None = None
        self._switch_neutral_angle: float | None = None
        self._last_switch_at = float("-inf")
        self._switch_direction = 0
        self._switch_direction_at: float | None = None
        self._thumb_candidate: Gesture | None = None
        self._thumb_candidate_at: float | None = None
        self._thumb_fired = False
        self._media_candidate: Gesture | None = None
        self._media_candidate_at: float | None = None
        self._media_last_fired_at = float("-inf")
        self._switch_active = False
        self._current_tilt = 0.0
        self._fist_wrist: NormalizedPoint | None = None
        self._fist_last_seen_at: float | None = None

    @property
    def mode(self) -> str | None:
        return self._mode

    @property
    def modifier_wrist(self) -> NormalizedPoint | None:
        return self._fist_wrist if self._mode == "switch" and self._switch_active else None

    @property
    def switch_tilt(self) -> float:
        return self._current_tilt

    def reset(self) -> Intent | None:
        release = Intent(IntentKind.SWITCH_END) if self._switch_active else None
        self._mode = None
        self._anchor = None
        self._axis = None
        self._switch_candidate_at = None
        self._switch_neutral_angle = None
        self._switch_direction = 0
        self._switch_direction_at = None
        self._thumb_candidate = None
        self._thumb_candidate_at = None
        self._thumb_fired = False
        self._media_candidate = None
        self._media_candidate_at = None
        self._media_last_fired_at = float("-inf")
        self._current_tilt = 0.0
        self._fist_wrist = None
        self._fist_last_seen_at = None
        self._switch_active = False
        return release

    def _scroll(self, tip: NormalizedPoint) -> Intent | None:
        if self._mode != "scroll" or self._anchor is None:
            self._mode = "scroll"
            self._anchor = tip
            self._axis = None
            return None

        dx = tip.x - self._anchor.x
        dy = tip.y - self._anchor.y
        if self._axis is None:
            if max(abs(dx), abs(dy)) < self.settings.scroll_step:
                return None
            self._axis = "horizontal" if abs(dx) > abs(dy) else "vertical"

        displacement = dx if self._axis == "horizontal" else dy
        if abs(displacement) < self.settings.scroll_step:
            return None
        direction = (1 if displacement > 0 else -1) if self._axis == "horizontal" else (-1 if displacement > 0 else 1)
        self._anchor = tip
        return Intent(
            IntentKind.SCROLL_HORIZONTAL
            if self._axis == "horizontal"
            else IntentKind.SCROLL_VERTICAL,
            amount=direction,
        )

    @staticmethod
    def _wrist_angle(points: tuple[NormalizedPoint, ...]) -> float:
        wrist = points[0]
        palm_x = (points[5].x + points[17].x) / 2
        palm_y = (points[5].y + points[17].y) / 2
        return degrees(atan2(palm_y - wrist.y, palm_x - wrist.x))

    def _switch(self, points: tuple[NormalizedPoint, ...], now: float) -> Intent | None:
        angle = self._wrist_angle(points)
        if self._mode != "switch":
            self._mode = "switch"
            self._switch_candidate_at = now
            self._switch_neutral_angle = angle
            self._current_tilt = 0.0
            return None

        if not self._switch_active:
            if self._switch_candidate_at is None or now - self._switch_candidate_at < self.settings.switch_hold_seconds:
                return None
            self._switch_active = True
            self._last_switch_at = now
            return Intent(IntentKind.SWITCH_BEGIN)

        if self._switch_neutral_angle is None:
            self._switch_neutral_angle = angle
            return None
        tilt = (angle - self._switch_neutral_angle + 180) % 360 - 180
        self._current_tilt = tilt
        if abs(tilt) < self.settings.switch_tilt_degrees:
            self._switch_direction = 0
            self._switch_direction_at = None
            self._last_switch_at = float("-inf")
            return None

        direction = 1 if tilt > 0 else -1
        if direction != self._switch_direction:
            self._switch_direction = direction
            self._switch_direction_at = now
            self._last_switch_at = now
            return Intent(
                IntentKind.SWITCH_NEXT if direction > 0
                else IntentKind.SWITCH_PREVIOUS
            )

        if (
            self._switch_direction_at is not None
            and now - self._switch_direction_at
            < self.settings.switch_repeat_delay_seconds
        ):
            return None
        speed = min(
            1.0,
            (abs(tilt) - self.settings.switch_tilt_degrees)
            / max(
                1.0,
                self.settings.switch_full_speed_degrees
                - self.settings.switch_tilt_degrees,
            ),
        )
        interval = (
            self.settings.switch_slow_interval_seconds
            - speed
            * (
                self.settings.switch_slow_interval_seconds
                - self.settings.switch_fast_interval_seconds
            )
        )
        if now - self._last_switch_at < interval:
            return None
        self._last_switch_at = now
        return Intent(
            IntentKind.SWITCH_NEXT if direction > 0
            else IntentKind.SWITCH_PREVIOUS
        )

    def _thumb_shortcut(self, gesture: Gesture, now: float) -> Intent | None:
        if self._mode != "thumb" or self._thumb_candidate is not gesture:
            self._mode = "thumb"
            self._thumb_candidate = gesture
            self._thumb_candidate_at = now
            self._thumb_fired = False
            return None
        if self._thumb_fired or self._thumb_candidate_at is None:
            return None
        if now - self._thumb_candidate_at < self.settings.thumb_hold_seconds:
            return None
        self._thumb_fired = True
        return Intent(
            IntentKind.UNDO if gesture is Gesture.THUMBS_LEFT else IntentKind.REDO
        )

    def _media(self, gesture: Gesture, points: tuple[NormalizedPoint, ...], now: float) -> Intent | None:
        if self._mode != "media" or self._media_candidate is not gesture:
            self._mode = "media"
            self._media_candidate = gesture
            self._media_candidate_at = now
            self._media_last_fired_at = float("-inf")
            return None
        if self._media_candidate_at is None or now - self._media_candidate_at < self.settings.media_hold_seconds:
            return None
        if gesture in (Gesture.THUMBS_UP, Gesture.THUMBS_DOWN):
            if now - self._media_last_fired_at < self.settings.volume_repeat_seconds:
                return None
            self._media_last_fired_at = now
            return Intent(IntentKind.VOLUME_UP if gesture is Gesture.THUMBS_UP else IntentKind.VOLUME_DOWN)
        if self._media_last_fired_at != float("-inf"):
            return None
        self._media_last_fired_at = now
        if gesture is Gesture.OPEN_PALM:
            return Intent(IntentKind.MEDIA_PLAY_PAUSE)
        direction = ((points[8].x + points[20].x) / 2) - points[0].x
        if abs(direction) < 0.07:
            return None
        return Intent(IntentKind.MEDIA_NEXT if direction > 0 else IntentKind.MEDIA_PREVIOUS)

    def update(
        self,
        gestures: tuple[Gesture, Gesture] | None,
        landmarks: tuple[tuple[NormalizedPoint, ...], tuple[NormalizedPoint, ...]] | None,
        *,
        armed: bool,
        now: float | None = None,
    ) -> Intent | None:
        now = monotonic() if now is None else now
        if not armed or gestures is None or landmarks is None:
            return self.reset()

        fist_indexes = [
            index for index, gesture in enumerate(gestures)
            if gesture in (Gesture.FIST, Gesture.CLOSED_HAND)
        ]
        if len(fist_indexes) == 1:
            fist_index = fist_indexes[0]
            self._fist_wrist = landmarks[fist_index][0]
            self._fist_last_seen_at = now
        elif (
            self._switch_active
            and not fist_indexes
            and self._fist_wrist is not None
            and self._fist_last_seen_at is not None
            and now - self._fist_last_seen_at <= self.settings.fist_grace_seconds
        ):
            fist_index = min(
                range(2),
                key=lambda index: distance(landmarks[index][0], self._fist_wrist),
            )
        else:
            return self.reset()
        active_index = 1 - fist_index
        active_gesture = gestures[active_index]
        active_points = landmarks[active_index]

        if self._switch_active:
            # Al inclinar la V su etiqueta puede fluctuar; el puño conserva Alt.
            if active_gesture not in (Gesture.THUMBS_LEFT, Gesture.THUMBS_RIGHT):
                return self._switch(active_points, now)
            return self.reset()

        if active_gesture is Gesture.POINTING:
            return self._scroll(active_points[8])
        if active_gesture in (Gesture.VICTORY, Gesture.PINCH_PREPARATION):
            return self._switch(active_points, now)
        if active_gesture in (Gesture.THUMBS_LEFT, Gesture.THUMBS_RIGHT):
            return self._thumb_shortcut(active_gesture, now)
        if active_gesture in (Gesture.THUMBS_UP, Gesture.THUMBS_DOWN, Gesture.OPEN_PALM, Gesture.ROCK):
            return self._media(active_gesture, active_points, now)

        return self.reset()
