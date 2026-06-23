from __future__ import annotations

import json
import struct
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence, Union

RAW_MAGIC = b"TISRAW\x01"


@dataclass(frozen=True)
class RawCaptureMetadata:
    device_model: str
    device_serial: str
    mode: str
    width: int
    height: int
    fps: float
    duration_s: float
    exposure_us: float
    pixel_format: str
    bits_per_pixel: int
    frame_count: int
    frame_size_bytes: int
    pitch_bytes: int
    created_at_utc: str
    frame_timestamps_ns: Sequence[int]
    frame_numbers: Sequence[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_raw_capture(
    output_path: Union[str, Path],
    frames: Sequence[bytes],
    metadata: RawCaptureMetadata,
) -> tuple[Path, Path]:
    output_path = Path(output_path).expanduser().resolve()
    if output_path.suffix.lower() != ".raw":
        output_path = output_path.with_suffix(".raw")

    meta_path = output_path.with_suffix(".raw.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = struct.pack(
        "<8sIIIIIddI",
        RAW_MAGIC,
        metadata.width,
        metadata.height,
        metadata.bits_per_pixel,
        metadata.frame_count,
        metadata.frame_size_bytes,
        metadata.fps,
        metadata.exposure_us,
        len(metadata.pixel_format.encode("utf-8")),
    )

    with output_path.open("wb") as raw_file:
        raw_file.write(header)
        raw_file.write(metadata.pixel_format.encode("utf-8"))
        for frame in frames:
            raw_file.write(frame)

    with meta_path.open("w", encoding="utf-8") as meta_file:
        json.dump(metadata.to_dict(), meta_file, indent=2)

    return output_path, meta_path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
