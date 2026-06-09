"""REST client for the ZMetrics backend.

Thin wrapper over httpx. Call groups mirror the backend routers (quarries, passports,
reports, ...). Network calls must run off the Qt UI thread (QThreadPool workers).
"""
from zmetrics_desktop.api.client import ApiClient, ApiError

__all__ = ["ApiClient", "ApiError"]
