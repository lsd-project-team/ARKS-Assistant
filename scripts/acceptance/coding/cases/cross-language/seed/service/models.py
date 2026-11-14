"""用户模型。"""

from dataclasses import dataclass


@dataclass
class User:
    id: int
    first: str
    last: str
