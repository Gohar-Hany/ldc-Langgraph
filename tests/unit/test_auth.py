from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.schemas.auth_schema import UserRole


def test_password_hashing():
    password = "SuperSecretPassword123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_encoding_and_decoding():
    user_id = "agent_42"
    role = UserRole.SENIOR_AGENT.value
    
    token = create_access_token(subject=user_id, role=role)
    payload = decode_access_token(token)
    
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert "exp" in payload


def test_invalid_jwt_token():
    invalid_token = "invalid.token.string"
    payload = decode_access_token(invalid_token)
    assert payload is None
