"""统计报表。"""


def counts(service):
    return {
        "books": len(service.repository.books),
        "members": len(service.repository.members),
        "active": len(service.active_loans()),
    }


def loans_by_member(service):
    result = {}
    for loan in service.repository.loans:
        name = service.repository.members[loan.member_id].name
        result[name] = result.get(name, 0) + 1
    return result
