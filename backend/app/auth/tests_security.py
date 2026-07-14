from __future__ import annotations

from app.auth.security import generate_session_token, hash_password, verify_password


def test_hash_password_generates_salt_when_omitted():
    password_hash, salt = hash_password("correct horse battery staple")
    assert password_hash
    assert salt


def test_verify_password_accepts_correct_password():
    password_hash, salt = hash_password("hunter2")
    assert verify_password("hunter2", password_hash, salt) is True


def test_verify_password_rejects_wrong_password():
    password_hash, salt = hash_password("hunter2")
    assert verify_password("wrong-password", password_hash, salt) is False


def test_same_password_different_salts_produce_different_hashes():
    hash1, salt1 = hash_password("same-password")
    hash2, salt2 = hash_password("same-password")
    assert salt1 != salt2
    assert hash1 != hash2


def test_generate_session_token_is_unique_and_nonempty():
    tokens = {generate_session_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) > 20 for t in tokens)
