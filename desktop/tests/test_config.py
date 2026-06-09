from zmetrics_desktop.config import Settings


def test_defaults_build_api_base():
    s = Settings()
    assert s.api_base == "http://localhost:8000/api/v1"
    assert s.oidc_issuer == "http://localhost:8080/realms/zmetrics"
    assert s.keycloak_client_id == "zmetrics-desktop"


def test_env_override(monkeypatch):
    monkeypatch.setenv("ZMETRICS_BACKEND_BASE_URL", "https://api.example.com/")
    monkeypatch.setenv("ZMETRICS_KEYCLOAK_REALM", "prod")
    s = Settings()
    assert s.api_base == "https://api.example.com/api/v1"
    assert s.oidc_issuer.endswith("/realms/prod")
