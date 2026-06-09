"""Application context: wires settings, auth, and the API client together.

Single composition point so UI code never constructs services itself. The ApiClient
pulls its bearer from the keyring-backed TokenStore and refreshes once on 401 via the
AuthManager.
"""
from __future__ import annotations

from dataclasses import dataclass

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.auth.oidc import AuthManager
from zmetrics_desktop.auth.token_store import TokenStore
from zmetrics_desktop.config import Settings, load_settings
from zmetrics_desktop.offline.sync_manager import SyncManager
from zmetrics_desktop.offline.sync_processor import SyncProcessor


@dataclass
class AppContext:
    settings: Settings
    auth: AuthManager
    api: ApiClient

    def make_sync_manager(self) -> SyncManager:
        """SyncManager is per-thread (sqlite3); create one where it is used."""
        return SyncManager(self.settings.offline_db_path)

    def make_sync_processor(self, queue: SyncManager) -> SyncProcessor:
        """Processor over a caller-owned (per-thread) queue."""
        return SyncProcessor(self.api, queue)

    @classmethod
    def build(cls) -> AppContext:
        settings = load_settings()
        store = TokenStore()
        auth = AuthManager(settings, token_store=store)
        api = ApiClient(
            settings,
            token_provider=store.access_token,
            refresher=auth.refresh,
        )
        return cls(settings=settings, auth=auth, api=api)
