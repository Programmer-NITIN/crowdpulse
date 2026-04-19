"""
google_services/firestore_client.py
-------------------------------------
Firestore persistence layer with transparent mock fallback.

Design:
- In production: stores crowd snapshots and navigation sessions to Firestore.
- In development: uses an OrderedDict bounded to 500 entries as an in-memory store.
- The mock store implements the same async-friendly API so callers never
  need to know which backend is active.
"""

import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_MOCK_ENTRIES = 500


class _MockFirestoreStore:
    """Bounded in-memory OrderedDict that mimics Firestore's basic operations."""

    def __init__(self, max_entries: int = _MAX_MOCK_ENTRIES) -> None:
        self._data: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max = max_entries

    def set_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> None:
        key = f"{collection}/{doc_id}"
        self._data[key] = {**data, "_stored_at": time.time()}
        while len(self._data) > self._max:
            self._data.popitem(last=False)

    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        return self._data.get(f"{collection}/{doc_id}")

    def list_collection(self, collection: str) -> list[Dict[str, Any]]:
        prefix = f"{collection}/"
        return [v for k, v in self._data.items() if k.startswith(prefix)]

    def clear(self) -> None:
        self._data.clear()

    @property
    def size(self) -> int:
        return len(self._data)


# ── Client initialization ───────────────────────────────────────────────────
_client: Any = None
_mock_store = _MockFirestoreStore()
_using_mock = True

if settings.firestore_enabled and settings.gcp_project_id:
    try:
        from google.cloud import firestore
        _client = firestore.Client(project=settings.gcp_project_id)
        _using_mock = False
        logger.info("Firestore: Connected to project '%s'.", settings.gcp_project_id)
    except Exception as exc:
        logger.warning("Firestore: Live connection failed — using mock. Error: %s", exc)
else:
    logger.info("Firestore: Running in mock mode (FIRESTORE_ENABLED=false).")


# ── Public API ───────────────────────────────────────────────────────────────

def store_document(collection: str, doc_id: str, data: Dict[str, Any]) -> None:
    """Persists a document to Firestore (or mock store)."""
    if _using_mock:
        _mock_store.set_document(collection, doc_id, data)
        return

    try:
        _client.collection(collection).document(doc_id).set(data)
    except Exception as exc:
        logger.error("Firestore: Write failed — falling back to mock. %s", exc)
        _mock_store.set_document(collection, doc_id, data)


def get_document(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a document from Firestore (or mock store)."""
    if _using_mock:
        return _mock_store.get_document(collection, doc_id)

    try:
        doc = _client.collection(collection).document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as exc:
        logger.error("Firestore: Read failed — falling back to mock. %s", exc)
        return _mock_store.get_document(collection, doc_id)


def list_documents(collection: str) -> list[Dict[str, Any]]:
    """Lists all documents in a collection."""
    if _using_mock:
        return _mock_store.list_collection(collection)

    try:
        docs = _client.collection(collection).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as exc:
        logger.error("Firestore: List failed — falling back to mock. %s", exc)
        return _mock_store.list_collection(collection)


def is_using_mock() -> bool:
    """Returns True if running in mock mode (for health checks)."""
    return _using_mock
