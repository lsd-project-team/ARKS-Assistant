"""数据模型。"""

from dataclasses import asdict, dataclass


@dataclass
class Book:
    id: int
    title: str
    author: str
    year: int


@dataclass
class Member:
    id: int
    name: str


@dataclass
class Loan:
    book_id: int
    member_id: int
    due: str
    returned: bool = False

    def to_dict(self):
        return asdict(self)
