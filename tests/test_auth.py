from api.auth import create_session_cookie, hash_password, read_session_cookie, verify_password


def test_verify_password_accepts_correct_password():
    stored = hash_password("password123")
    assert verify_password("password123", stored) is True


def test_verify_password_rejects_wrong_password():
    stored = hash_password("password123")
    assert verify_password("wrong-password", stored) is False


def test_hash_password_uses_a_random_salt_each_time():
    assert hash_password("password123") != hash_password("password123")


def test_session_cookie_round_trips_user_id():
    token = create_session_cookie(42)
    assert read_session_cookie(token) == 42


def test_session_cookie_rejects_tampered_token():
    token = create_session_cookie(42)
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert read_session_cookie(tampered) is None


def test_session_cookie_rejects_garbage():
    assert read_session_cookie("not-a-real-token") is None
