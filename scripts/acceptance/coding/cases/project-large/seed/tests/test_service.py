import pytest

from library import LibraryService


def service():
    return LibraryService()


def test_add_book():
    book = service().add_book("Clean Code", "Robert Martin", 2008)
    assert book.id == 1 and book.title == "Clean Code"


def test_add_book_invalid_year():
    with pytest.raises(ValueError):
        service().add_book("x", "y", 999)


def test_register_member():
    member = service().register_member("张三")
    assert member.id == 1 and member.name == "张三"


def test_loan_and_return():
    svc = service()
    book = svc.add_book("A", "B", 2020)
    member = svc.register_member("张三")
    loan = svc.loan(book.id, member.id, "2026-01-01")
    assert loan.returned is False
    assert svc.return_book(book.id).returned is True


def test_loan_unknown_book():
    svc = service()
    member = svc.register_member("张三")
    with pytest.raises(KeyError):
        svc.loan(99, member.id, "2026-01-01")


def test_loan_twice_rejected():
    svc = service()
    book = svc.add_book("A", "B", 2020)
    member = svc.register_member("张三")
    svc.loan(book.id, member.id, "2026-01-01")
    with pytest.raises(ValueError):
        svc.loan(book.id, member.id, "2026-01-02")


def test_return_unknown():
    with pytest.raises(KeyError):
        service().return_book(1)


def test_overdue():
    svc = service()
    book = svc.add_book("A", "B", 2020)
    member = svc.register_member("张三")
    svc.loan(book.id, member.id, "2026-01-01")
    assert len(svc.overdue("2026-02-01")) == 1
    assert svc.overdue("2025-12-01") == []


def test_active_loans_excludes_returned():
    svc = service()
    book = svc.add_book("A", "B", 2020)
    member = svc.register_member("张三")
    svc.loan(book.id, member.id, "2026-01-01")
    svc.return_book(book.id)
    assert svc.active_loans() == []


def test_ids_increment():
    svc = service()
    assert svc.add_book("A", "B", 2020).id == 1
    assert svc.add_book("C", "D", 2021).id == 2
