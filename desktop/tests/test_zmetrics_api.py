import json

import httpx

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.config import Settings

_QUARRY = {"id": "q1", "name": "Карьер 1", "location_description": None,
           "latitude": 55.0, "longitude": 61.0}
_REPORT = {"id": "r1", "title": "⚠ Mock pipeline — Granulometric Analysis (P80=312mm)",
           "report_type": "granulometric", "analysis_method": "mock",
           "analysis_result_id": "ar1", "confidence_score": 0.72,
           "model_version_tag": None, "created_at": "2026-06-10T12:00:00Z"}
_RESULT = {"id": "ar1", "p10_mm": 95.2, "p50_mm": 210.7, "p80_mm": 312.4,
           "rosin_rammler_n": 1.8, "rosin_rammler_xc": 240.0,
           "oversize_percent": 4.2, "fines_percent": 8.1,
           "confidence_score": 0.72, "confidence_notes": "mock pipeline",
           "size_distribution": [{"size_mm": 100, "cumulative_passing_pct": 12.5},
                                  {"size_mm": 300, "cumulative_passing_pct": 78.0}]}


def _api(handler) -> ZMetricsApi:
    client = ApiClient(Settings(), transport=httpx.MockTransport(handler))
    return ZMetricsApi(client)


def _paginated(items: list[dict]) -> dict:
    return {"items": items, "total": len(items), "page": 1, "page_size": 50}


def test_list_quarries_unwraps_pagination():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/quarries"
        return httpx.Response(200, json=_paginated([_QUARRY]))

    quarries = _api(handler).list_quarries()
    assert len(quarries) == 1
    assert quarries[0].name == "Карьер 1"
    assert quarries[0].latitude == 55.0


def test_analysis_result_parses_size_distribution():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/analysis-results/ar1"
        return httpx.Response(200, json=_RESULT)

    result = _api(handler).get_analysis_result("ar1")
    assert result.p80_mm == 312.4  # full precision, no rounding
    assert len(result.size_distribution) == 2
    assert result.size_distribution[1].cumulative_passing_pct == 78.0


def test_report_keeps_mock_method():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_paginated([_REPORT]))

    reports = _api(handler).list_reports("q1")
    assert reports[0].analysis_method == "mock"
    assert "⚠" in reports[0].title


def test_dto_ignores_unknown_fields():
    quarry = dict(_QUARRY, brand_new_field="from a newer backend")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_paginated([quarry]))

    assert _api(handler).list_quarries()[0].id == "q1"


def test_transition_passport_posts_to_action_url():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(200, json={
            "id": "p1", "site_section_id": "s1", "status": "submitted",
            "revision_number": 1, "created_at": "2026-06-10", "updated_at": "2026-06-10",
        })

    passport = _api(handler).transition_passport("q1", "p1", "submit")
    assert seen["path"] == "/api/v1/quarries/q1/passports/p1/submit"
    assert passport.status == "submitted"


def test_upload_artifact_sends_multipart():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["content_type"] = request.headers["Content-Type"]
        seen["body"] = request.read()
        return httpx.Response(201, json={
            "id": "a1", "capture_session_id": "cs1", "artifact_type": "left_frame",
            "storage_bucket": "zmetrics-frames", "storage_key": "sessions/cs1/left.jpg",
            "frame_index": 0,
        })

    artifact = _api(handler).upload_artifact("cs1", b"\xff\xd8jpegdata", "left_frame", 0)
    assert artifact.artifact_type == "left_frame"
    assert seen["content_type"].startswith("multipart/form-data")
    assert b"left_frame" in seen["body"]
    assert b"jpegdata" in seen["body"]


def test_review_recommendation_sends_status_and_notes():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["json"] = json.loads(request.read())
        return httpx.Response(200, json={
            "id": "rec1", "report_id": "r1", "status": "accepted",
            "recommendation_text": "...", "created_at": "2026-06-10",
        })

    rec = _api(handler).review_recommendation("r1", "rec1", "accepted", "ок")
    assert rec.status == "accepted"
    assert seen["json"] == {"status": "accepted", "reviewer_notes": "ок"}
