"""Escucha local de la frase Hey Jarvis y captura una orden corta."""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from queue import Empty, SimpleQueue
from threading import Event, Thread
from time import monotonic
from pathlib import Path

import numpy as np

from asistente_jarvis.speech.assistant_actions import open_start_app, parse_open_app
from asistente_jarvis.speech.dictation import DictationController


@dataclass(frozen=True, slots=True)
class VoiceEvent:
    kind: str
    message: str = ""


class VoiceAssistantController:
    sample_rate = 16000
    frame_samples = 1280  # 80 ms, formato esperado por openWakeWord

    def __init__(self, dictation: DictationController, *, threshold: float = 0.5) -> None:
        self.dictation = dictation
        self.threshold = threshold
        self.state = "idle"
        self._events: SimpleQueue[VoiceEvent] = SimpleQueue()
        self._stop = Event()
        self._pause = Event()
        self._paused_ack = Event()
        self._thread: Thread | None = None
        self._busy = False
        self._warmup_error: Exception | None = None
        self._warmup_thread: Thread | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="jarvis-wake-word", daemon=True)
        self._thread.start()

    def pause(self, timeout: float = 3.0) -> bool:
        if self.busy or self.state in ("command", "processing"):
            return False
        self._pause.set()
        if self._thread is None or not self._thread.is_alive():
            return True
        paused = self._paused_ack.wait(timeout)
        if not paused:
            self._pause.clear()
        return paused

    def resume(self) -> None:
        self._pause.clear()
        self._paused_ack.clear()

    def poll(self) -> list[VoiceEvent]:
        events: list[VoiceEvent] = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except Empty:
                return events

    def _emit(self, kind: str, message: str = "") -> None:
        self._events.put(VoiceEvent(kind, message))

    def _run(self) -> None:
        try:
            import openwakeword
            from openwakeword.model import Model

            wake_paths = [
                Path(path) for path in openwakeword.get_pretrained_model_paths("onnx")
                if "hey_jarvis" in path
            ]
            if not wake_paths or not wake_paths[0].is_file():
                raise FileNotFoundError(
                    "Falta el modelo Hey Jarvis. Ejecuta `uv run asistente-jarvis prepare-wake-word`."
                )
            wake_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            self._emit("state", "Hey Jarvis: escucha local activa")
            import sounddevice as sd

            device_index = self.dictation._input_device(sd)
            device_name = sd.query_devices(device_index, "input")["name"]
            self._emit("microphone", f"Micrófono: {device_name} ({device_index})")
            history: deque[np.ndarray] = deque(maxlen=6)
            while not self._stop.is_set():
                if self._pause.is_set():
                    history.clear()
                    wake_model.reset()
                    self.state = "paused"
                    self._paused_ack.set()
                    while self._pause.is_set() and not self._stop.wait(0.1):
                        pass
                    self._paused_ack.clear()
                    self.state = "idle"
                    continue
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    device=device_index,
                    blocksize=self.frame_samples,
                ) as stream:
                    self.state = "wake"
                    while not self._stop.is_set() and not self._pause.is_set():
                        block, _overflowed = stream.read(self.frame_samples)
                        audio = np.clip(block[:, 0] * 32768, -32768, 32767).astype(np.int16)
                        history.append(audio)
                        scores = wake_model.predict(audio)
                        score = max(scores.values(), default=0.0)
                        if score >= self.threshold:
                            self._emit("wake", "Hey Jarvis")
                            self.state = "command"
                            self._warmup_error = None
                            self._warmup_thread = Thread(
                                target=self._warm_up_whisper,
                                name="jarvis-whisper-warmup",
                                daemon=True,
                            )
                            self._warmup_thread.start()
                            pre_roll = np.concatenate(tuple(history)).astype(np.float32) / 32768
                            command = self._capture_command(stream, pre_roll)
                            if command is not None and not self._pause.is_set():
                                self._handle_command(command)
                            wake_model.reset()
                            history.clear()
                            self.state = "wake"
        except Exception as exc:
            if not self._stop.is_set():
                self.state = "error"
                self._emit("error", str(exc))
        finally:
            if self.state != "error":
                self.state = "stopped"
            self._paused_ack.set()

    def _capture_command(self, stream: object, pre_roll: np.ndarray) -> np.ndarray | None:
        parts = [pre_roll]
        speech_started: float | None = None
        last_voice: float | None = None
        started = monotonic()
        while not self._stop.is_set() and not self._pause.is_set():
            if monotonic() - started >= 8.0:
                break
            block, _overflowed = stream.read(self.frame_samples)
            samples = block[:, 0].copy()
            parts.append(samples)
            now = monotonic()
            level = float(np.sqrt(np.mean(np.square(samples))))
            if level >= 0.003:
                speech_started = speech_started or now
                last_voice = now
            if speech_started is None and now - started >= 3.0:
                return None
            if last_voice is not None and now - last_voice >= 0.75:
                break
        if speech_started is None:
            return None
        audio = np.concatenate(parts)
        # Excluir el comienzo del wake word, conservando un margen para la orden.
        return audio[int(0.35 * self.sample_rate):]

    def _handle_command(self, audio: np.ndarray) -> None:
        self._busy = True
        self.state = "processing"
        self._emit("state", "Procesando orden con Whisper…")
        try:
            if self._warmup_thread is not None:
                self._warmup_thread.join()
            if self._warmup_error is not None:
                raise self._warmup_error
            transcript = self.dictation.transcribe_utterance(audio)
            if not transcript:
                self._emit("ignored", "No se reconoció una orden")
                return
            self._emit("transcript", transcript)
            app_name = parse_open_app(transcript)
            if app_name is None:
                self._emit("ignored", "Por ahora solo puedo abrir aplicaciones: di «abre Spotify»")
                return
            open_start_app(app_name)
            self._emit("action", f"Abriendo {app_name}")
        except Exception as exc:
            self._emit("error", f"Orden de voz: {exc}")
        finally:
            self._busy = False
            self.state = "wake"

    def _warm_up_whisper(self) -> None:
        try:
            self.dictation._load_model()
        except Exception as exc:
            self._warmup_error = exc

    def close(self) -> None:
        self._stop.set()
        self._pause.clear()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
