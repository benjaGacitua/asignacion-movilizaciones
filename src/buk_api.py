import logging
from dataclasses import dataclass
from datetime import date

import requests

from .config import BUK

logger = logging.getLogger(__name__)

_SESSION = requests.Session()


@dataclass
class AssignPayload:
    employee_id: int
    item_id: int
    start_date: date
    description: str
    amount: int


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "auth_token": BUK.api_key,
    }


def assigned_item_ids(employee_id: int) -> set[int]:
    """item_ids ya asignados al empleado en Buk."""
    url = f"{BUK.base_url}/api/v1/chile/employees/{employee_id}/assigns"
    logger.debug("GET %s", url)
    response = _SESSION.get(url, headers=_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()
    ids = {
        a["item"]["id"]
        for a in data.get("data", [])
        if a.get("item", {}).get("id") is not None
    }
    logger.debug("employee_id=%s items ya asignados: %s", employee_id, sorted(ids))
    return ids


def assign_mobility(payload: AssignPayload) -> dict:
    url = f"{BUK.base_url}/api/v1/chile/assigns"
    body = {
        "employee_id": payload.employee_id,
        "item_id": payload.item_id,
        "start_date": payload.start_date.strftime("%Y-%m-%d"),
        "end_date": "",
        "description": payload.description,
        "amount": payload.amount,
        "advance_payment_day": "",
        "overwrite_existing_assign": False,
        "cost_center": "",
    }
    logger.debug(
        "POST %s — employee_id=%s item_id=%s amount=%s",
        url, payload.employee_id, payload.item_id, payload.amount,
    )
    response = _SESSION.post(url, headers=_headers(), json=body, timeout=30)
    response.raise_for_status()
    return response.json()
