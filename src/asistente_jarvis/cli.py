from __future__ import annotations

import argparse
from pathlib import Path
import sys

from asistente_jarvis.config.paths import DEFAULT_MODEL_PATH, DEFAULT_WHISPER_MODEL_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asistente-jarvis",
        description="Prototipo local de reconocimiento de manos y gestos.",
    )
    subparsers = parser.add_subparsers(dest="command")

    for command, description in (
        ("preview", "Muestra landmarks y gestos reconocidos."),
        ("control", "Controla mouse, atajos y dictado con gestos."),
    ):
        vision = subparsers.add_parser(command, help=description)
        vision.add_argument("--camera", type=int, default=0, help="Índice de cámara (por defecto: 0).")
        vision.add_argument(
            "--backend",
            choices=("auto", "dshow", "msmf"),
            default="auto",
            help="Backend de cámara para Windows (por defecto: auto).",
        )
        vision.add_argument(
            "--model",
            type=Path,
            default=DEFAULT_MODEL_PATH,
            help=f"Ruta al modelo Hand Landmarker (por defecto: {DEFAULT_MODEL_PATH}).",
        )
        vision.add_argument(
            "--no-mirror",
            action="store_true",
            help="No refleja horizontalmente la imagen de la cámara.",
        )
        if command == "control":
            vision.add_argument(
                "--sensitivity",
                type=float,
                default=None,
                help="Velocidad relativa del cursor (0.1 a 4.0; reemplaza la calibración guardada en esta sesión).",
            )
            vision.add_argument(
                "--select-all-mode",
                choices=("auto", "ctrl-a", "ctrl-e"),
                default="auto",
                help="Atajo para seleccionar todo (por defecto: auto según la aplicación).",
            )
            vision.add_argument(
                "--microphone", type=int, default=None,
                help="Índice del micrófono; por defecto usa el dispositivo de entrada de Windows.",
            )
            vision.add_argument(
                "--speech-device", choices=("auto", "cuda", "cpu"), default="auto",
                help="Procesador de Whisper (auto intenta CUDA y luego CPU).",
            )
            vision.add_argument(
                "--speech-language", default="es",
                help="Idioma del dictado en código ISO; por defecto: es.",
            )

    download = subparsers.add_parser(
        "download-model", help="Descarga el modelo oficial de Hand Landmarker."
    )
    download.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Ruta de salida (por defecto: {DEFAULT_MODEL_PATH}).",
    )
    download.add_argument("--force", action="store_true", help="Reemplaza un modelo existente.")
    speech = subparsers.add_parser(
        "prepare-speech", help="Descarga Whisper large-v3 para el dictado local."
    )
    speech.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_WHISPER_MODEL_PATH,
        help=f"Directorio del modelo (por defecto: {DEFAULT_WHISPER_MODEL_PATH}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "download-model":
            from asistente_jarvis.vision.model import download_hand_landmarker

            path = download_hand_landmarker(args.output, force=args.force)
            print(f"Modelo disponible en: {path}")
            return 0

        if args.command == "prepare-speech":
            from asistente_jarvis.speech.model import download_whisper_large_v3

            path = download_whisper_large_v3(args.output)
            print(f"Whisper large-v3 disponible en: {path}")
            return 0

        if args.command in ("preview", "control"):
            from asistente_jarvis.vision.preview import PreviewOptions, run_preview

            options = PreviewOptions(
                camera_index=args.camera,
                backend=args.backend,
                mirror=not args.no_mirror,
                model_path=args.model,
                control_mouse=args.command == "control",
                sensitivity=getattr(args, "sensitivity", None),
                select_all_mode=getattr(args, "select_all_mode", "auto"),
                microphone=getattr(args, "microphone", None),
                speech_device=getattr(args, "speech_device", "auto"),
                speech_language=getattr(args, "speech_language", "es"),
            )
            return run_preview(options)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Comando desconocido: {args.command}")
    return 2
