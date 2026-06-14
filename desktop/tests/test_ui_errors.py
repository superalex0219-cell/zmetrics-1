from zmetrics_desktop.ui.errors import human_error


def test_human_error_maps_connection_refused():
    assert "Сервер недоступен" in human_error("[Errno 61] Connection refused")


def test_human_error_maps_camera_access():
    assert "Нет доступа к камере" in human_error("Cannot open camera #0")
