from dataclasses import dataclass
from typing import Any

from cryptobot._utils import parse_json


@dataclass
class CrytoBotError(Exception):
    code: int
    name: str

    @classmethod
    def from_json(cls, json: Any) -> "CrytoBotError":
        return parse_json(cls, **json)

    def __str__(self):
        return f"code={self.code}, name={self.name}"
