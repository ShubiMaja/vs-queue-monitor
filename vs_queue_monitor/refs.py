"""Variable-like objects for headless monitoring (``.get()`` / ``.set()`` / ``trace_add``)."""

from __future__ import annotations

from typing import Any, Callable


class StrRef:
    __slots__ = ("_value", "_traces")

    def __init__(self, value: str = "") -> None:
        self._value = value
        self._traces: dict[str, list[Callable[..., None]]] = {}

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value
        for seq in self._traces.values():
            for cb in seq:
                try:
                    cb("", "", "write")
                except Exception:
                    pass

    def trace_add(self, mode: str, callback: Callable[..., None]) -> str:
        key = f"id{len(self._traces)}"
        self._traces.setdefault(key, []).append(callback)
        return key

    def trace_remove(self, tid: str) -> None:
        self._traces.pop(tid, None)


class BoolRef:
    __slots__ = ("_value", "_traces")

    def __init__(self, value: bool = False) -> None:
        self._value = bool(value)
        self._traces: dict[str, list[Callable[..., None]]] = {}

    def get(self) -> bool:
        return self._value

    def set(self, value: Any) -> None:
        self._value = bool(value)
        for seq in self._traces.values():
            for cb in seq:
                try:
                    cb("", "", "write")
                except Exception:
                    pass

    def trace_add(self, mode: str, callback: Callable[..., None]) -> str:
        key = f"id{len(self._traces)}"
        self._traces.setdefault(key, []).append(callback)
        return key

    def trace_remove(self, tid: str) -> None:
        self._traces.pop(tid, None)
