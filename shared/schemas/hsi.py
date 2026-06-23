from __future__ import annotations

from pydantic import BaseModel, Field


class Roi(BaseModel):
    x: int = 0
    y: int = 0
    width: int
    height: int


class BuildParams(BaseModel):
    source_path: str
    build_mode: str
    data_source: str = "raw"
    reconstruction: dict = Field(default_factory=dict)
    roi: Roi
    wavelengths_nm: list[float] | None = None
    calibration_profile: str = "default"
    output_name: str | None = None


class BuildPreset(BaseModel):
    id: str
    name: str
    description: str | None = None


class CalibrationProfileInfo(BaseModel):
    name: str
    description: str | None = None
    roi: Roi | None = None
    wavelength_count: int | None = None


class BuildJobStatus(BaseModel):
    job_id: str
    status: str
    progress: float = 0.0
    stage: str | None = None
    message: str | None = None
    error: str | None = None


class HsiInfo(BaseModel):
    hsi_id: str
    hsi_path: str
    bands: int
    width: int
    height: int
    wavelengths_nm: list[float] = Field(default_factory=list)


class ExportRequest(BaseModel):
    format: str
    include_sidecars: bool = True
    bands: str = "all"


class ExportResult(BaseModel):
    export_path: str
    sidecar_paths: list[str] = Field(default_factory=list)
