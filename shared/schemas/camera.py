from __future__ import annotations

from pydantic import BaseModel, Field


class CameraStatus(BaseModel):
    connected: bool = False
    model: str | None = None
    serial: str | None = None
    vendor: str | None = None
    usb_speed: str | None = None
    preview_active: bool = False
    recording_active: bool = False
    error: str | None = None


class CaptureModeInfo(BaseModel):
    id: str
    width: int
    height: int
    fps: float
    pixel_formats: list[str] = Field(default_factory=lambda: ["Mono8", "Mono16"])


class CameraProperty(BaseModel):
    id: str
    type: str
    value: float | int | str | bool
    min: float | int | None = None
    max: float | int | None = None
    unit: str | None = None
    writable: bool = True
