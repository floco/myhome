from __future__ import annotations
from pydantic import BaseModel


class McpConfig(BaseModel):
    enabled: bool = False
