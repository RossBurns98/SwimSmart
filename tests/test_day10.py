from fastapi.testclient import TestClient
from swimsmart.api.main import create_app
from swimsmart.api.deps import get_db

def _client(db_session):
    app = create_app()
    def _override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    return TestClient(app)

def test_signup_and_login(db_session):
    client = _client(db_session)

    # signup
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "secret", "role": "swimmer"})
    assert r.status_code == 200
    uid = r.json()["id"]

    # login
    r = client.post("/auth/login", json={"email": "a@b.com", "password": "secret"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["user"]["id"] == uid
