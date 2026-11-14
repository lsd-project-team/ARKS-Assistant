from library import LibraryService, overdue_notices


def test_overdue_notice():
    svc = LibraryService()
    book = svc.add_book("A", "B", 2020)
    member = svc.register_member("张三")
    svc.loan(book.id, member.id, "2026-01-01")
    notices = overdue_notices(svc, "2026-02-01")
    assert len(notices) == 1
    assert "张三" in notices[0] and "A" in notices[0] and "2026-01-01" in notices[0]


def test_no_overdue():
    svc = LibraryService()
    book = svc.add_book("A", "B", 2020)
    member = svc.register_member("张三")
    svc.loan(book.id, member.id, "2026-03-01")
    assert overdue_notices(svc, "2026-02-01") == []


def test_multiple_overdue():
    svc = LibraryService()
    member = svc.register_member("张三")
    for index in range(2):
        book = svc.add_book(f"B{index}", "A", 2020)
        svc.loan(book.id, member.id, "2026-01-01")
    assert len(overdue_notices(svc, "2026-02-01")) == 2
