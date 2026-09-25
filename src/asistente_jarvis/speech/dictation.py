"""Captura continua y transcripción progresiva en memoria."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
import os
from pathlib import Path
from queue import Empty, Queue, SimpleQueue
from threading import Event, Thread
from time import monotonic
import sys

import numpy as np


_DLL_DIRECTORY_HANDLES: list[object] = []
_PRELOADED_DLLS: list[object] = []
_CUDA_LIBRARY_DIRECTORY: Path | None = None


def _make_cuda_libraries_visible() -> Path | None:
    """Encuentra CUDA/cuDNN ya instalados, incluso fuera del entorno de uv."""
    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return None
    global _CUDA_LIBRARY_DIRECTORY
    if _CUDA_LIBRARY_DIRECTORY is not None:
        return _CUDA_LIBRARY_DIRECTORY
    candidates: list[Path] = []
    extra = os.environ.get("JARVIS_CUDA_DLL_DIR")
    if extra:
        candidates.append(Path(extra))
    local_programs = Path.home() / "AppData" / "Local" / "Programs"
    candidates.extend(local_programs.glob("Python/Python3*/Lib/site-packages/torch/lib"))
    candidates.append(local_programs / "Ollama" / "lib" / "ollama" / "cuda_v12")
    for directory in candidates:
        if (directory / "cublas64_12.dll").is_file() and (directory / "cudnn64_9.dll").is_file():
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
            for name in ("cudart64_12.dll", "cublasLt64_12.dll", "cublas64_12.dll", "cudnn64_9.dll"):
                path = directory / name
                if path.is_file():
                    _PRELOADED_DLLS.append(ctypes.WinDLL(str(path)))
            _CUDA_LIBRARY_DIRECTORY = directory
            return directory
    return None


@dataclass(frozen=True, slots=True)
class SpeechEvent:
    session: int
    kind: str
    message: str = ""


class DictationController:
    sample_rate = 16000
    chunk_seconds = 3.0

    def __init__(
        self,
        model_path: Path,
        *,
        microphone: int | None = None,
        language: str = "es",
        device: str = "auto",
        max_seconds: float = 60.0,
    ) -> None:
        self.model_path = model_path
        self.microphone = microphone
        self.language = language
        self.device = device
        self.max_seconds = max_seconds
        self.state = "idle"
        self._session = 0
        self._stop = Event()
        self._cancel = Event()
        self._audio: Queue[np.ndarray | None] = Queue()
        self._events: SimpleQueue[SpeechEvent] = SimpleQueue()
        self._capture_thread: Thread | None = None
        self._transcribe_thread: Thread | None = None
        self._model: object | None = None
        self._loaded_device: str | None = None

    @property
    def busy(self) -> bool:
        return self.state != "idle"

    def _publish(self, session: int, kind: str, message: str = "") -> None:
        if not self._cancel.is_set():
            self._events.put(SpeechEvent(session, kind, message))

    def start(self) -> None:
        if self.busy:
            return
        if self._transcribe_thread is not None and self._transcribe_thread.is_alive():
            raise RuntimeError("El dictado anterior aún está terminando. Inténtalo en unos segundos.")
        if self._capture_thread is not None and self._capture_thread.is_alive():
            raise RuntimeError("El micrófono todavía se está cerrando. Inténtalo de nuevo.")
        if not (self.model_path / "model.bin").is_file():
            raise FileNotFoundError(
                f"No se encontró Whisper en {self.model_path}. "
                "Ejecuta `uv run asistente-jarvis prepare-speech`."
            )
        self._session += 1
        session = self._session
        self._stop = Event()
        self._cancel = Event()
        self._audio = Queue()
        self.state = "recording"
        self._transcribe_thread = Thread(
            target=self._transcribe, args=(session, self._audio, self._stop, self._cancel),
            daemon=True,
        )
        self._capture_thread = Thread(
            target=self._capture, args=(session, self._audio, self._stop, self._cancel),
            daemon=True,
        )
        self._transcribe_thread.start()
        self._capture_thread.start()

    def finish(self) -> None:
        if self.state == "recording":
            self.state = "finishing"
            self._stop.set()

    def cancel(self) -> None:
        if not self.busy:
            return
        self._cancel.set()
        self._stop.set()
        self._session += 1
        self.state = "idle"

    def poll(self) -> list[SpeechEvent]:
        events: list[SpeechEvent] = []
        while True:
            try:
                event = self._events.get_nowait()
            except Empty:
                break
            if event.session != self._session:
                continue
            if event.kind == "stopped":
                self.state = "finishing"
            elif event.kind in ("done", "error"):
                self.state = "idle"
            events.append(event)
        return events

    def _input_device(self, sd: object) -> int:
        if self.microphone is not None:
            info = sd.query_devices(self.microphone, "input")
            if info["max_input_channels"] < 1:
                raise RuntimeError(f"El dispositivo {self.microphone} no es un micrófono.")
            return self.microphone
        default_index = int(sd.default.device[0])
        if default_index >= 0:
            default_info = sd.query_devices(default_index, "input")
            if "realtek" in default_info["name"].lower():
                return default_index
        for index, info in enumerate(sd.query_devices()):
            name = info["name"].lower()
            if info["max_input_channels"] and "realtek" in name and (
                "mic" in name or "micr" in name
            ):
                return index
        if default_index >= 0:
            return default_index
        raise RuntimeError("No hay un micrófono de entrada disponible en Windows.")

    def _capture(
        self,
        session: int,
        audio_queue: Queue[np.ndarray | None],
        stop: Event,
        cancel: Event,
    ) -> None:
        try:
            import sounddevice as sd

            device_index = self._input_device(sd)
            device_name = sd.query_devices(device_index, "input")["name"]
            self._publish(session, "microphone", f"Micrófono: {device_name} ({device_index})")
            parts: list[np.ndarray] = []
            buffered = 0
            saw_voice = False
            silent_samples = 0
            began = monotonic()
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=device_index,
                blocksize=1024,
            ) as stream:
                while not stop.is_set() and not cancel.is_set():
                    block, _overflowed = stream.read(1024)
                    parts.append(block[:, 0].copy())
                    buffered += len(block)
                    level = float(np.sqrt(np.mean(np.square(block[:, 0]))))
                    if level >= 0.003:
                        saw_voice = True
                        silent_samples = 0
                    elif saw_voice:
                        silent_samples += len(block)
                    pause_ended_phrase = (
                        saw_voice
                        and buffered >= self.sample_rate * 0.7
                        and silent_samples >= self.sample_rate * 0.65
                    )
                    if pause_ended_phrase or buffered >= self.sample_rate * self.chunk_seconds:
                        audio_queue.put(np.concatenate(parts))
                        parts.clear()
                        buffered = 0
                        saw_voice = False
                        silent_samples = 0
                    if monotonic() - began >= self.max_seconds:
                        stop.set()
                        self._publish(session, "stopped", "Límite de 60 s; terminando dictado")
            if not cancel.is_set() and buffered >= self.sample_rate // 3:
                audio_queue.put(np.concatenate(parts))
        except Exception as exc:
            self._publish(session, "error", f"Micrófono: {exc}")
            stop.set()
        finally:
            audio_queue.put(None)

    def _load_model(self) -> object:
        if self._model is not None:
            return self._model
        if self.device in ("auto", "cuda"):
            try:
                _make_cuda_libraries_visible()
            except OSError:
                if self.device == "cuda":
                    raise
        from faster_whisper import WhisperModel

        if self.device in ("auto", "cuda"):
            try:
                self._model = WhisperModel(
                    str(self.model_path), device="cuda", compute_type="float16"
                )
                self._loaded_device = "cuda"
                return self._model
            except Exception:
                if self.device == "cuda":
                    raise
        self._model = WhisperModel(str(self.model_path), device="cpu", compute_type="int8")
        self._loaded_device = "cpu"
        return self._model

    def _transcribe_audio(self, audio: np.ndarray, session: int) -> str:
        model = self._load_model()
        try:
            return self._decode(model, audio)
        except Exception as exc:
            if self.device != "auto" or self._loaded_device != "cuda":
                raise
            self._model = None
            self._loaded_device = None
            from faster_whisper import WhisperModel

            self._model = WhisperModel(str(self.model_path), device="cpu", compute_type="int8")
            self._loaded_device = "cpu"
            self._publish(session, "fallback", f"CUDA no disponible ({exc}); usando CPU")
            return self._decode(self._model, audio)

    def _decode(self, model: object, audio: np.ndarray) -> str:
        segments, _info = model.transcribe(
            audio,
            language=self.language,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
            hotwords="coma, punto, dos puntos, Enter, Enviar, borrar palabra, borrar todo",
        )
        # La inferencia puede comenzar recién al iterar este generador.
        return " ".join(segment.text.strip() for segment in segments).strip()

    def _transcribe(
        self,
        session: int,
        audio_queue: Queue[np.ndarray | None],
        stop: Event,
        cancel: Event,
    ) -> None:
        try:
            self._load_model()
            last_backend: str | None = None
            while not cancel.is_set():
                audio = audio_queue.get()
                if audio is None:
                    break
                content = self._transcribe_audio(audio, session)
                if self._loaded_device != last_backend:
                    last_backend = self._loaded_device
                    self._publish(session, "backend", f"Whisper: {last_backend.upper()}")
                if content:
                    self._publish(session, "text", content)
            if not cancel.is_set():
                self._publish(session, "done")
        except Exception as exc:
            self._publish(session, "error", f"Whisper: {exc}")
            stop.set()

    def close(self) -> None:
        self.cancel()
