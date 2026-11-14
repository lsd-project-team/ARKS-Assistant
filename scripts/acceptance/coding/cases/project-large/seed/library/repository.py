"""内存仓储。"""


class Repository:
    def __init__(self):
        self.books = {}
        self.members = {}
        self.loans = []

    def next_book_id(self):
        return max(self.books, default=0) + 1

    def next_member_id(self):
        return max(self.members, default=0) + 1

    def add_book(self, book):
        self.books[book.id] = book

    def add_member(self, member):
        self.members[member.id] = member

    def add_loan(self, loan):
        self.loans.append(loan)

    def active_loan_for(self, book_id):
        for loan in self.loans:
            if loan.book_id == book_id and not loan.returned:
                return loan
        return None
