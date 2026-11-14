from library import hash_password, verify_password


def test_hash_is_stable():
    assert hash_password("secret") == hash_password("secret")
    assert len(hash_password("secret")) == 64


def test_verify_true():
    assert verify_password("secret", hash_password("secret")) is True


def test_verify_false():
    assert verify_password("wrong", hash_password("secret")) is False
