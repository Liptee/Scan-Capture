#!/usr/bin/env python3
"""Read a TIS RAW capture file and optionally export one frame as PGM."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

RAW_MAGIC = b"TISRAW\x01"


def read_raw(path: Path) -> tuple[dict, bytes]:
    meta_path = path.with_suffix(".raw.json")
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")

    with meta_path.open("r", encoding="utf-8") as meta_file:
        metadata = json.load(meta_file)

    with path.open("rb") as raw_file:
        header = raw_file.read(48)
        if len(header) < 48:
            raise ValueError("RAW file is too small")

        magic, width, height, bpp, frame_count, frame_size, fps, exposure_us, pf_len = struct.unpack(
            "<8sIIIIIddI", header
        )
        if magic != RAW_MAGIC:
            raise ValueError("Unsupported RAW file format")

        pixel_format = raw_file.read(pf_len).decode("utf-8")
        payload = raw_file.read()

    expected_size = frame_count * frame_size
    if len(payload) != expected_size:
        raise ValueError(
            f"Payload size mismatch: expected {expected_size} bytes, got {len(payload)}"
        )

    metadata["header_pixel_format"] = pixel_format
    metadata["header_fps"] = fps
    metadata["header_exposure_us"] = exposure_us
    return metadata, payload


def export_pgm(frame: bytes, width: int, height: int, max_value: int, output: Path) -> None:
    header = f"P5\n{width} {height}\n{max_value}\n".encode("ascii")
    with output.open("wb") as pgm_file:
        pgm_file.write(header)
        pgm_file.write(frame)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a TIS RAW capture file")
    parser.add_argument("raw_file", help="Path to .raw file")
    parser.add_argument(
        "--export-frame",
        type=int,
        default=None,
        help="Export frame index as PGM for quick visual check",
    )
    parser.add_argument(
        "--pgm-output",
        default="frame.pgm",
        help="Output PGM path for --export-frame",
    )
    args = parser.parse_args(argv)

    raw_path = Path(args.raw_file)
    metadata, payload = read_raw(raw_path)

    print(json.dumps(metadata, indent=2))

    if args.export_frame is not None:
        frame_size = metadata["frame_size_bytes"]
        index = args.export_frame
        if index < 0 or index >= metadata["frame_count"]:
            print("Frame index out of range", file=sys.stderr)
            return 2
        start = index * frame_size
        frame = payload[start : start + frame_size]
        max_value = (1 << metadata["bits_per_pixel"]) - 1
        if metadata["bits_per_pixel"] == 16:
            frame = frame[1::2]
            max_value = 255
        export_pgm(frame, metadata["width"], metadata["height"], max_value, Path(args.pgm_output))
        print(f"Exported frame {index} to {args.pgm_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
