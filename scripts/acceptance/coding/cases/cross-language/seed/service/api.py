"""JSON 序列化。"""


def to_payload(user):
    return {"id": user.id, "first": user.first, "last": user.last}


def list_payload(users):
    return [to_payload(user) for user in users]
