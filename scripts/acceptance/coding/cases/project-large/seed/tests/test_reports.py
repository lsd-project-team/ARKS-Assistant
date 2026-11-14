from library import LibraryService, counts, loans_by_member


def service():
    svc = LibraryService()
    first = svc.add_book("A", "B", 2020)
    second = svc.add_book("C", "D", 2021)
    member = svc.register_member("张三")
    svc.loan(first.id, member.id, "2026-01-01")
    svc.loan(second.id, member.id, "2026-01-02")
    return svc


def test_counts():
    assert counts(service()) == {"books": 2, "members": 1, "active": 2}


def test_counts_empty():
    assert counts(LibraryService()) == {"books": 0, "members": 0, "active": 0}


def test_loans_by_member():
    assert loans_by_member(service()) == {"张三": 2}


def test_loans_by_member_multiple():
    svc = service()
    other = svc.register_member("李四")
    third = svc.add_book("E", "F", 2022)
    svc.loan(third.id, other.id, "2026-01-03")
    assert loans_by_member(svc) == {"张三": 2, "李四": 1}


def test_counts_after_return():
    svc = service()
    svc.return_book(1)
    assert counts(svc)["active"] == 1
