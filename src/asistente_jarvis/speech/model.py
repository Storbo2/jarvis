from __future__ import annotations

from pathlib import Path


WHISPER_REPOSITORY = "Systran/faster-whisper-large-v3"
WHISPER_FILES = (
    "config.json",
    "model.bin",
    "preprocessor_config.json",
    "tokenizer.json",
    "vocabulary.json",
)


def download_whisper_large_v3(destination: Path) -> Path:
    """Descarga pesos y configuración; no carga ni ejecuta el modelo."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "Instala las dependencias del proyecto con `uv sync`."
        ) from exc

    destination = destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=WHISPER_REPOSITORY,
        local_dir=destination,
        allow_patterns=list(WHISPER_FILES),
    )
    missing = [name for name in WHISPER_FILES if not (destination / name).is_file()]
    if missing:
        raise RuntimeError(f"La descarga de Whisper quedó incompleta: {', '.join(missing)}")
    return destination
