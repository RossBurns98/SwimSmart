import os
from fastapi.testclient import TestClient
from swimsmart.api.main import create_app

def test_health_ok():
    app = create_app()
    client = TestClient(app)
    r = client.get("/system/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_version_uses_env_vars(monkeypatch):
    monkeypatch.setenv("SWIMSMART_VERSION", "9.9.9")
    monkeypatch.setenv("SWIMSMART_ENV", "production")
    app = create_app()
    client = TestClient(app)
    r = client.get("/system/version")
    assert r.status_code == 200
    assert r.json() == {"version": "9.9.9", "env": "production"}
