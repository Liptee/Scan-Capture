from __future__ import annotations

from typing import Protocol

from shared.schemas.hsi import (
    BuildJobStatus,
    BuildParams,
    BuildPreset,
    CalibrationProfileInfo,
    ExportRequest,
    ExportResult,
    HsiInfo,
)


class IHsiBuildService(Protocol):
    def list_presets(self) -> list[BuildPreset]: ...

    def list_calibration_profiles(self) -> list[CalibrationProfileInfo]: ...

    def validate_params(self, params: BuildParams) -> list[str]: ...

    async def start_build(self, params: BuildParams) -> str: ...

    def get_job_status(self, job_id: str) -> BuildJobStatus: ...

    async def cancel_build(self, job_id: str) -> None: ...

    def get_result(self, job_id: str) -> HsiInfo: ...

    async def export(self, hsi_id: str, request: ExportRequest) -> ExportResult: ...
