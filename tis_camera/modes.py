from __future__ import annotations

import re
from dataclasses import dataclass

from .device_info import DMM_37UX252_ML, KNOWN_PRESET_MODES

MODE_PATTERN = re.compile(
    r"^(?P<width>\d+)x(?P<height>\d+)@(?P<fps>\d+(?:\.\d+)?)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CaptureMode:
    width: int
    height: int
    fps: float

    def as_string(self) -> str:
        fps_text = f"{self.fps:g}"
        return f"{self.width}x{self.height}@{fps_text}"

    @property
    def frame_interval_s(self) -> float:
        return 1.0 / self.fps


def parse_mode(mode: str) -> CaptureMode:
    match = MODE_PATTERN.match(mode.strip())
    if not match:
        raise ValueError(
            f"Invalid mode '{mode}'. Expected format WIDTHxHEIGHT@FPS, "
            "for example 2048x1536@60"
        )

    width = int(match.group("width"))
    height = int(match.group("height"))
    fps = float(match.group("fps"))

    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("Mode width, height and fps must be positive")

    if width > DMM_37UX252_ML.max_width or height > DMM_37UX252_ML.max_height:
        raise ValueError(
            f"Resolution {width}x{height} exceeds sensor maximum "
            f"{DMM_37UX252_ML.max_width}x{DMM_37UX252_ML.max_height}"
        )

    return CaptureMode(width=width, height=height, fps=fps)


def static_preset_modes() -> list[CaptureMode]:
    return [CaptureMode(width, height, fps) for width, height, fps in KNOWN_PRESET_MODES]
