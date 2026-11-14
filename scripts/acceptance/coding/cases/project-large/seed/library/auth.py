"""密码哈希。"""

import hashlib


def hash_password(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_password(raw, hashed):
    return hash_password(raw) == hashed
