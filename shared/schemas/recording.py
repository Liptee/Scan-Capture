from __future__ import annotations

from pydantic import BaseModel, Field


class RecordingConfig(BaseModel):
    mode: str = Field(..., description="WIDTHxHEIGHT@FPS")
    pixel_format: str = "mono16"
    exposure_us: float = Field(..., gt=0)
    max_duration_s: float | None = Field(None, description="None = manual stop only")
    output_name: str | None = None


class RecordingStatus(BaseModel):
    recording_id: str
    status: str
    elapsed_s: float = 0.0
    frame_count: int = 0
    duration_s: float | None = None
    file_path: str | None = None
    metadata_path: str | None = None
    error: str | None = None
