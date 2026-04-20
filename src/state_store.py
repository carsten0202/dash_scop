from threading import RLock
from typing import Any


class AppStateStore:
    def __init__(self):
        self._datasets: dict[str, dict[str, Any]] = {}
        self._selections: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def get_dataset(self, key: str | None) -> dict[str, Any] | None:
        if not key:
            return None
        with self._lock:
            return self._datasets.get(key)

    def put_dataset(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._datasets[key] = value

    def delete_dataset(self, key: str | None) -> dict[str, Any] | None:
        if not key:
            return None
        with self._lock:
            return self._datasets.pop(key, None)

    def get_selection(self, key: str | None) -> dict[str, Any] | None:
        if not key:
            return None
        with self._lock:
            return self._selections.get(key)

    def put_selection(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._selections[key] = value

    def delete_selection(self, key: str | None) -> dict[str, Any] | None:
        if not key:
            return None
        with self._lock:
            return self._selections.pop(key, None)
