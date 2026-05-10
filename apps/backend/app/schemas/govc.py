from typing import Any

from pydantic import BaseModel


class GovcResult(BaseModel):
    command: str
    args: list[str]
    data: Any
