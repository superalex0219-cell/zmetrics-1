"""Offline-first store-and-forward queue (SQLite).

All write operations (create capture_session, upload frames, create passport) go through
the ``SyncManager``. Each queued item carries a client-generated ``idempotency_key`` so
the server de-duplicates retries. See ``sync_manager.SyncManager``.
"""
from zmetrics_desktop.offline.sync_manager import PendingUpload, SyncManager

__all__ = ["SyncManager", "PendingUpload"]
