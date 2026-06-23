from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceSpec:
    model: str
    vendor: str
    sensor: str
    sensor_type: str
    shutter: str
    max_width: int
    max_height: int
    max_fps: float
    pixel_size_um: float
    dynamic_range_bits: int
    exposure_min_us: float
    exposure_max_us: float
    usb_interface: str
    pixel_formats: tuple[str, ...]


DMM_37UX252_ML = DeviceSpec(
    model="DMM 37UX252-ML",
    vendor="The Imaging Source Europe GmbH",
    sensor="Sony IMX252",
    sensor_type="CMOS Pregius",
    shutter="Global",
    max_width=2048,
    max_height=1536,
    max_fps=119.0,
    pixel_size_um=3.45,
    dynamic_range_bits=12,
    exposure_min_us=1.0,
    exposure_max_us=4_000_000.0,
    usb_interface="USB 3.1",
    pixel_formats=("Mono8", "Mono16"),
)


KNOWN_PRESET_MODES: tuple[tuple[int, int, float], ...] = (
    (2048, 1536, 119.0),
    (2048, 1536, 60.0),
    (2048, 1536, 30.0),
    (2048, 1536, 15.0),
    (2048, 1024, 90.0),
    (2048, 768, 120.0),
    (1920, 1080, 90.0),
    (1600, 1200, 90.0),
    (1280, 1024, 120.0),
    (1280, 720, 150.0),
    (1024, 768, 150.0),
    (800, 600, 200.0),
    (640, 480, 250.0),
)
