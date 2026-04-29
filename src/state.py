import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class StateManager:
    def __init__(self, state_file: Path):
        self._path = state_file
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        return {"sent": []}

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def _key(employee_id: int, month: str) -> str:
        return f"{employee_id}_{month}"

    def is_sent(self, employee_id: int, month: str) -> bool:
        key = self._key(employee_id, month)
        return any(
            r["key"] == key and r["status"] == "success"
            for r in self._data["sent"]
        )

    def mark_sent(self, employee_id: int, month: str, status: str, detail: str = ""):
        record = {
            "key": self._key(employee_id, month),
            "employee_id": employee_id,
            "month": month,
            "sent_at": datetime.now(tz=timezone.utc).isoformat(),
            "status": status,
            "detail": detail,
        }
        self._data["sent"].append(record)
        self._save()
        logger.debug("Estado guardado: %s → %s", record["key"], status)
