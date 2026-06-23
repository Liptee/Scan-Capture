#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from tis_camera.device_info import DMM_37UX252_ML
from tis_camera.ic4_backend import (
    BackendNotAvailableError,
    PlatformNotSupportedError,
    capture_to_raw,
)
from tis_camera.modes import parse_mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture RAW frames from a The Imaging Source USB3 Vision camera "
            f"({DMM_37UX252_ML.model})."
        )
    )
    parser.add_argument(
        "--mode",
        required=True,
        help="Capture mode in WIDTHxHEIGHT@FPS format, for example 2048x1536@60",
    )
    parser.add_argument(
        "--duration",
        type=float,
        required=True,
        help="Capture duration in seconds",
    )
    parser.add_argument(
        "--exposure",
        type=float,
        required=True,
        help="Exposure time in microseconds",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output RAW file path (.raw). Metadata is written to .raw.json",
    )
    parser.add_argument(
        "--pixel-format",
        default="mono16",
        choices=["mono8", "mono16"],
        help="Pixel format for capture (default: mono16)",
    )
    parser.add_argument(
        "--serial",
        default=None,
        help="Camera serial number or model substring. Uses the first camera if omitted.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.duration <= 0:
        print("duration must be positive", file=sys.stderr)
        return 2
    if args.exposure <= 0:
        print("exposure must be positive", file=sys.stderr)
        return 2

    try:
        mode = parse_mode(args.mode)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    try:
        raw_path, meta_path = capture_to_raw(
            mode=mode,
            duration_s=args.duration,
            exposure_us=args.exposure,
            output_path=args.output,
            pixel_format=args.pixel_format,
            serial=args.serial,
        )
    except PlatformNotSupportedError as exc:
        print(exc, file=sys.stderr)
        return 3
    except BackendNotAvailableError as exc:
        print(exc, file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"Capture failed: {exc}", file=sys.stderr)
        return 1

    print(f"Saved RAW data: {raw_path}")
    print(f"Saved metadata: {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
