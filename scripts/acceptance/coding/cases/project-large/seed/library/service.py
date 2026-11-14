"""借阅服务。"""

from .models import Book, Loan, Member
from .repository import Repository


class LibraryService:
    def __init__(self, repository=None):
        self.repository = repository or Repository()

    def add_book(self, title, author, year):
        title, author = title.strip(), author.strip()
        if not title or not author:
            raise ValueError("书名和作者不能为空")
        if not 1000 <= int(year) <= 2100:
            raise ValueError("年份超出范围")
        book = Book(id=self.repository.next_book_id(), title=title, author=author, year=int(year))
        self.repository.add_book(book)
        return book

    def register_member(self, name):
        name = name.strip()
        if not name:
            raise ValueError("姓名不能为空")
        member = Member(id=self.repository.next_member_id(), name=name)
        self.repository.add_member(member)
        return member

    def loan(self, book_id, member_id, due):
        if book_id not in self.repository.books:
            raise KeyError(book_id)
        if member_id not in self.repository.members:
            raise KeyError(member_id)
        if self.repository.active_loan_for(book_id) is not None:
            raise ValueError("该书已借出")
        loan = Loan(book_id=book_id, member_id=member_id, due=due)
        self.repository.add_loan(loan)
        return loan

    def return_book(self, book_id):
        loan = self.repository.active_loan_for(book_id)
        if loan is None:
            raise KeyError(book_id)
        loan.returned = True
        return loan

    def active_loans(self):
        return [loan for loan in self.repository.loans if not loan.returned]

    def overdue(self, today):
        return [loan for loan in self.active_loans() if loan.due < today]
