from zmetrics_desktop.config import Settings, save_user_server_settings, user_env_path


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


def test_save_user_server_settings_preserves_unknown_lines(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = user_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# local config\nOTHER=value\nZMETRICS_BACKEND_BASE_URL=http://old\n", encoding="utf-8")

    saved = save_user_server_settings({
        "backend_base_url": "http://192.168.0.10:8000",
        "keycloak_base_url": "http://192.168.0.10:8080",
        "keycloak_realm": "zmetrics",
        "keycloak_client_id": "zmetrics-desktop",
        "request_timeout_s": 5.0,
    })

    assert saved == path
    content = path.read_text(encoding="utf-8")
    assert "# local config" in content
    assert "OTHER=value" in content
    assert "ZMETRICS_BACKEND_BASE_URL=http://192.168.0.10:8000" in content
    assert "ZMETRICS_KEYCLOAK_BASE_URL=http://192.168.0.10:8080" in content
