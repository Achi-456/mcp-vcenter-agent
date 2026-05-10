from typing import Any

from pydantic import BaseModel


class VSphereRestResult(BaseModel):
    endpoint: str
    data: Any
