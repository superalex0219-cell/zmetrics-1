"""Human-friendly messages for UI error labels."""
from __future__ import annotations


def human_error(message: str) -> str:
    text = (message or "").strip()
    lowered = text.lower()
    if not text:
        return ""
    if "403" in text:
        return "Недостаточно прав"
    if "401" in text:
        return "Сессия истекла. Войдите снова."
    if (
        "connection refused" in lowered
        or "errno 61" in lowered
        or "connecterror" in lowered
        or "all connection attempts failed" in lowered
        or "failed to establish a new connection" in lowered
    ):
        return (
            "Сервер недоступен. Проверьте адрес сервера в разделе "
            "«Подключение» и убедитесь, что сервер запущен в локальной сети."
        )
    if "timed out" in lowered or "timeout" in lowered:
        return "Сервер не ответил вовремя. Проверьте сеть и адрес подключения."
    if "nodename nor servname" in lowered or "name or service not known" in lowered:
        return "Не удалось найти сервер по этому адресу. Проверьте IP или имя хоста."
    if "cannot open camera" in lowered:
        return "Нет доступа к камере или она занята другим приложением."
    if "failed to read a frame" in lowered:
        return "Камера подключена, но кадр не читается. Переподключите ZED 2 и попробуйте снова."
    if "camera is not open" in lowered:
        return "Камера не открыта. Выберите камеру и запустите превью."
    return text
