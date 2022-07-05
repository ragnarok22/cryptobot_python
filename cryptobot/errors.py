from dataclasses import dataclass


@dataclass
class CrytoBotError(Exception):
    code: int
    name: str

    def __str__(self):
        return f"code={self.code}, name={self.name}"
