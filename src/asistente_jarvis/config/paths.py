from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "hand_landmarker.task"
DEFAULT_WHISPER_MODEL_PATH = PROJECT_ROOT / "models" / "whisper" / "large-v3"
