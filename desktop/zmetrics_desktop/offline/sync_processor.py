"""Drains the offline queue against the REST API.

A queue item is dispatched by its ``kind`` through a handler registry, so screens can
register new operation kinds without touching the processor. Retry semantics:

- success → the item is removed;
- ``ApiError`` (server answered with an error) → ``mark_failure``; the item retires to
  ``failed()`` after ``MAX_ATTEMPTS`` and is surfaced to the user;
- transport error (connectivity dropped mid-drain) → the pass stops WITHOUT counting an
  attempt — losing the network is not the item's fault.

The client-side ``idempotency_key`` only guards against double-enqueueing locally; the
backend has no Idempotency-Key support yet, so a request that succeeded server-side but
failed to deliver its response may duplicate on retry (accepted for now, see roadmap).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import httpx

from zmetrics_desktop.api.client import ApiClient, ApiError
from zmetrics_desktop.offline.sync_manager import PendingUpload, SyncManager

# Sends one queued operation; raises ApiError / httpx errors on failure.
Handler = Callable[[ApiClient, PendingUpload], None]


@dataclass(frozen=True)
class SyncReport:
    """Outcome of one drain pass — shown in the status bar."""

    online: bool
    sent: int = 0
    failed: int = 0
    remaining: int = 0


def _post_json(api: ApiClient, item: PendingUpload) -> None:
    """Generic handler: ``payload = {"path": "/quarries", "json": {...}}``."""
    api.post(item.payload["path"], json=item.payload["json"])


def default_handlers() -> dict[str, Handler]:
    """Built-in operation kinds. Screens extend this as they are ported."""
    return {"post_json": _post_json}


class SyncProcessor:
    """One drain pass over the pending queue. Not thread-safe (owns a SyncManager)."""

    def __init__(
        self,
        api: ApiClient,
        queue: SyncManager,
        handlers: dict[str, Handler] | None = None,
    ) -> None:
        self._api = api
        self._queue = queue
        self._handlers = handlers if handlers is not None else default_handlers()

    def process_once(self) -> SyncReport:
        """Drain the queue if the backend is reachable; otherwise report offline."""
        if not self._api.is_reachable():
            return SyncReport(online=False, remaining=len(self._queue.pending()))

        sent = failed = 0
        for item in self._queue.pending():
            handler = self._handlers.get(item.kind)
            if handler is None:
                self._queue.mark_failure(item.idempotency_key, f"unknown kind: {item.kind}")
                failed += 1
                continue
            try:
                handler(self._api, item)
            except ApiError as exc:
                self._queue.mark_failure(item.idempotency_key, str(exc))
                failed += 1
            except httpx.HTTPError as exc:
                # Connectivity dropped mid-drain: keep the item as-is, stop this pass.
                _ = exc
                break
            else:
                self._queue.remove(item.idempotency_key)
                sent += 1

        return SyncReport(
            online=True,
            sent=sent,
            failed=failed,
            remaining=len(self._queue.pending()),
        )
