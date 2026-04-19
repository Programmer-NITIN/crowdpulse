"""
tests/test_auth.py
------------------
Tests for Firebase Authentication verification.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.google_services.firebase_auth import verify_token, is_using_mock

client = TestClient(app)


class TestFirebaseAuthClient:
    def test_is_using_mock(self):
        assert is_using_mock() is True

    def test_mock_token_accepted(self):
        claims = verify_token("mock-user123")
        assert claims is not None
        assert claims["uid"] == "user123"
        assert "email" in claims

    def test_mock_token_email_format(self):
        claims = verify_token("mock-testid")
        assert claims["email"] == "testid@mock.crowdpulse.dev"

    def test_invalid_token_rejected(self):
        claims = verify_token("invalid-token")
        assert claims is None

    def test_empty_token_rejected(self):
        claims = verify_token("")
        assert claims is None


class TestAuthEndpoint:
    def test_missing_authorization_header(self):
        resp = client.get("/auth/verify")
        assert resp.status_code == 401

    def test_malformed_authorization(self):
        resp = client.get("/auth/verify", headers={"Authorization": "Basic abc123"})
        assert resp.status_code == 401

    def test_valid_mock_token(self):
        resp = client.get("/auth/verify", headers={"Authorization": "Bearer mock-webuser"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["uid"] == "webuser"
        assert data["email"] == "webuser@mock.crowdpulse.dev"

    def test_invalid_token_returns_401(self):
        headers = {"Authorization": "Bearer real-token-no-firebase"}
        resp = client.get("/auth/verify", headers=headers)
        assert resp.status_code == 401

    def test_bearer_prefix_required(self):
        resp = client.get("/auth/verify", headers={"Authorization": "mock-user"})
        assert resp.status_code == 401
