"""逾期通知。"""


def overdue_notices(service, today):
    notices = []
    for loan in service.overdue(today):
        book = service.repository.books[loan.book_id]
        member = service.repository.members[loan.member_id]
        notices.append(f"{member.name}: {book.title} 逾期（应还 {loan.due}）")
    return notices
