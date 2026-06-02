from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from services.config import DATA_DIR


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean(value: object, default: str = "") -> str:
    return str(value or default).strip()


def _owner_id(identity: dict[str, object]) -> str:
    return _clean(identity.get("id")) or "anonymous"


def _timestamp(value: object) -> float:
    if not isinstance(value, str) or not value.strip():
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _clone_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _normalize_conversation(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    conversation_id = _clean(value.get("id"))
    if not conversation_id:
        return None
    now = _now_iso()
    item = _clone_json(value)
    item["id"] = conversation_id
    item["title"] = _clean(item.get("title"))
    item["createdAt"] = _clean(item.get("createdAt"), now)
    item["updatedAt"] = _clean(item.get("updatedAt"), item["createdAt"])
    if not isinstance(item.get("turns"), list):
        item["turns"] = []
    return item


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: _timestamp(item.get("updatedAt")), reverse=True)


def _pick_latest(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    return incoming if _timestamp(incoming.get("updatedAt")) >= _timestamp(current.get("updatedAt")) else current


class ImageConversationService:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._items_by_owner = self._load()

    def list(self, identity: dict[str, object]) -> dict[str, Any]:
        owner = _owner_id(identity)
        with self._lock:
            return {"items": _sort_items([_clone_json(item) for item in self._items_by_owner.get(owner, [])])}

    def save_many(self, identity: dict[str, object], items: list[Any]) -> dict[str, Any]:
        owner = _owner_id(identity)
        with self._lock:
            current_items = self._items_by_owner.get(owner, [])
            item_map = {item["id"]: item for item in current_items if isinstance(item, dict) and item.get("id")}
            for raw_item in items:
                item = _normalize_conversation(raw_item)
                if not item:
                    continue
                current = item_map.get(item["id"])
                item_map[item["id"]] = _pick_latest(current, item) if current else item
            self._items_by_owner[owner] = _sort_items(list(item_map.values()))[:500]
            self._save()
            return self.list(identity)

    def save_one(self, identity: dict[str, object], item: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_conversation(item)
        if not normalized:
            return self.list(identity)
        result = self.save_many(identity, [normalized])
        return {"item": normalized, "items": result["items"]}

    def rename(self, identity: dict[str, object], conversation_id: str, title: str) -> dict[str, Any]:
        owner = _owner_id(identity)
        with self._lock:
            items = self._items_by_owner.get(owner, [])
            now = _now_iso()
            for item in items:
                if item.get("id") == conversation_id:
                    item["title"] = _clean(title)
                    item["updatedAt"] = now
                    break
            self._items_by_owner[owner] = _sort_items(items)
            self._save()
            return self.list(identity)

    def delete(self, identity: dict[str, object], conversation_id: str) -> dict[str, Any]:
        owner = _owner_id(identity)
        with self._lock:
            self._items_by_owner[owner] = [
                item for item in self._items_by_owner.get(owner, []) if item.get("id") != conversation_id
            ]
            self._save()
            return self.list(identity)

    def clear(self, identity: dict[str, object]) -> dict[str, Any]:
        owner = _owner_id(identity)
        with self._lock:
            self._items_by_owner[owner] = []
            self._save()
            return {"items": []}

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        raw_owners = raw.get("owners") if isinstance(raw, dict) else {}
        if not isinstance(raw_owners, dict):
            return {}
        owners: dict[str, list[dict[str, Any]]] = {}
        for owner, items in raw_owners.items():
            if not isinstance(items, list):
                continue
            normalized = [item for item in (_normalize_conversation(raw_item) for raw_item in items) if item]
            owners[_clean(owner)] = _sort_items(normalized)
        return owners

    def _save(self) -> None:
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps({"owners": self._items_by_owner}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self.path)


image_conversation_service = ImageConversationService(DATA_DIR / "image_conversations.json")
