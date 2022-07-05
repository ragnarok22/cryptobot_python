from dataclasses import dataclass
from typing import Optional


@dataclass
class CrytoBotError(Exception):
    status_code: int
    error: str
    message: Optional[str]
