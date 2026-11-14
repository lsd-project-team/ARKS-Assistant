from service import User, list_payload, to_payload


def test_payload_fields():
    payload = to_payload(User(1, "Ada", "Lovelace"))
    assert payload["id"] == 1
    assert payload["first"] == "Ada"
    assert payload["last"] == "Lovelace"


def test_list_payload():
    users = [User(1, "Ada", "Lovelace"), User(2, "Alan", "Turing")]
    assert len(list_payload(users)) == 2


def test_list_payload_empty():
    assert list_payload([]) == []


def test_unicode_names():
    payload = to_payload(User(3, "张", "三"))
    assert payload["first"] == "张" and payload["last"] == "三"


def test_ids_are_ints():
    payload = to_payload(User(7, "A", "B"))
    assert payload["id"] == 7
