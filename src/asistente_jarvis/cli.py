from __future__ import annotations

import argparse
from pathlib import Path
import sys

from asistente_jarvis.config.paths import DEFAULT_MODEL_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asistente-jarvis",
        description="Prototipo local de reconocimiento de manos y gestos.",
    )
    subparsers = parser.add_subparsers(dest="command")

    for command, description in (
        ("preview", "Muestra landmarks y gestos reconocidos."),
        ("control", "Controla el mouse con índice, pinza y palma abierta."),
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
                default=0.8,
                help="Velocidad relativa del cursor (0.1 a 2.0; por defecto: 0.8).",
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

        if args.command in ("preview", "control"):
            from asistente_jarvis.vision.preview import PreviewOptions, run_preview

            options = PreviewOptions(
                camera_index=args.camera,
                backend=args.backend,
                mirror=not args.no_mirror,
                model_path=args.model,
                control_mouse=args.command == "control",
                sensitivity=getattr(args, "sensitivity", 0.8),
            )
            return run_preview(options)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Comando desconocido: {args.command}")
    return 2
