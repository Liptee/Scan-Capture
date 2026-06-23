from __future__ import annotations

from typing import Protocol


class IStageController(Protocol):
    """Заглушка для v2: управление подвижкой."""

    async def get_position(self) -> float: ...

    async def move_to(self, position: float, speed: float) -> None: ...

    async def stop(self) -> None: ...
