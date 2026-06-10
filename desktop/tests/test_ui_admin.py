"""Offscreen tests for the admin screen: 403 wording, temp-password lifecycle, roles."""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

import httpx
import pytest

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.config import Settings
from zmetrics_desktop.models import AdminUser, UserQuarryAccess

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from zmetrics_desktop.ui.admin import AdminScreen, human_error  # noqa: E402
from zmetrics_desktop.ui.state import AppState  # noqa: E402

_USER = AdminUser(id="u1", email="ivan@example.com", full_name="Иван Петров",
                  is_active=True, created_at="2026-06-10T10:00:00Z")
_ACCESS = UserQuarryAccess(access_id="a1", quarry_id="q1", quarry_name="Карьер 1",
                           role_name="blaster", role_level=3)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    return app or QApplication([])


@pytest.fixture(autouse=True)
def sync_submit(monkeypatch):
    def run_inline(fn, on_success=None, on_error=None):
        try:
            result = fn()
        except Exception as exc:
            if on_error is not None:
                on_error(str(exc))
        else:
            if on_success is not None:
                on_success(result)

    monkeypatch.setattr("zmetrics_desktop.ui.admin.submit", run_inline)


def _screen(handler) -> AdminScreen:
    context = SimpleNamespace(api=ApiClient(Settings(), transport=httpx.MockTransport(handler)))
    return AdminScreen(context, AppState())


def _empty_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})


def test_human_error_maps_403():
    assert human_error("HTTP 403: Admin role required") == "Недостаточно прав"
    assert human_error("HTTP 409: User already exists") == "HTTP 409: User already exists"


def test_forbidden_shows_no_data(qapp):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"detail": "Admin role required"})

    screen = _screen(handler)
    screen.refresh()
    assert screen._error_label.text() == "Недостаточно прав"
    assert screen._table.rowCount() == 0


def test_users_render_with_status(qapp):
    screen = _screen(_empty_handler)
    inactive = AdminUser(id="u2", email="x@y.z", full_name="Экс",
                         is_active=False, created_at="2026-06-01T00:00:00Z")
    screen._render_users([_USER, inactive])
    assert screen._table.item(0, 2).text() == "Активен"
    assert screen._table.item(1, 2).text() == "Отключён"


def test_temp_password_shown_once_and_cleared(qapp):
    screen = _screen(_empty_handler)
    screen._show_password("ivan@example.com", "Xk9-temp")
    assert screen._password_box.isVisibleTo(screen)
    assert "Xk9-temp" in screen._password_label.text()
    assert "больше не будет показан" in screen._password_label.text()

    screen._clear_password()
    assert not screen._password_box.isVisibleTo(screen)
    assert screen._temp_password is None
    assert "Xk9-temp" not in screen._password_label.text()


def test_create_user_shows_password_from_response(qapp):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST" and request.url.path == "/api/v1/admin/users":
            return httpx.Response(201, json={
                "user": _USER.model_dump(), "temporary_password": "Tmp-123-Pass",
            })
        return _empty_handler(request)

    screen = _screen(handler)

    # сабмит как из диалога — без UI-цикла
    def created(result):
        screen._show_password(result.user.email, result.temporary_password)

    result = screen._api.admin_create_user("ivan@example.com", "Иван Петров")
    created(result)
    assert "Tmp-123-Pass" in screen._password_label.text()
    body = json.loads([r for r in requests if r.method == "POST"][0].read())
    assert body == {"email": "ivan@example.com", "full_name": "Иван Петров"}


def test_create_dialog_rejects_cyrillic_email(qapp):
    from zmetrics_desktop.ui.admin import UserCreateDialog

    dialog = UserCreateDialog()
    dialog._full_name.setText("Иван Петров")
    dialog._email.setText("иван@тест.рф")  # Keycloak такое отвергает — ловим до запроса
    dialog._validate_and_accept()
    assert dialog.email is None
    assert "латиницей" in dialog._error.text()

    dialog._email.setText("ivan@test.com")
    dialog._validate_and_accept()
    assert dialog.email == "ivan@test.com"


def test_access_list_renders_roles(qapp):
    screen = _screen(_empty_handler)
    screen._render_accesses([_ACCESS])
    assert screen._access_table.item(0, 0).text() == "Карьер 1"
    assert screen._access_table.item(0, 1).text() == "blaster"


def test_grant_access_posts_role(qapp):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(201, json={"id": "a2"})
        if request.url.path.endswith("/access"):
            return httpx.Response(200, json=[_ACCESS.model_dump()])
        return _empty_handler(request)

    screen = _screen(handler)
    screen._selected = _USER
    screen._grant_quarry_combo.addItem("Карьер 1", "q1")
    screen._grant_role_combo.setCurrentText("surveyor")
    screen._grant_access()

    posts = [r for r in requests if r.method == "POST"]
    assert len(posts) == 1
    assert posts[0].url.path == "/api/v1/admin/quarries/q1/access"
    assert json.loads(posts[0].read())["role_name"] == "surveyor"
    # список ролей перезагружен
    assert screen._access_table.rowCount() == 1
