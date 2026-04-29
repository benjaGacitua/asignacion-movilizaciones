import logging
from dataclasses import dataclass
from datetime import date

import requests

from .config import BUK

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_MOBILITY_ITEM_IDS = {1751, 2108}


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


def has_mobility_assign(employee_id: int) -> bool:
    url = f"{BUK.base_url}/api/v1/chile/employees/{employee_id}/assigns"
    logger.debug("GET %s", url)
    response = _SESSION.get(url, headers=_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()
    assigns = data if isinstance(data, list) else data.get("assigns", [])
    found = any(a.get("item_id") in _MOBILITY_ITEM_IDS for a in assigns)
    if found:
        matched = [a.get("item_id") for a in assigns if a.get("item_id") in _MOBILITY_ITEM_IDS]
        logger.debug("employee_id=%s ya tiene asignación de movilización: item_ids=%s", employee_id, matched)
    return found


def assign_mobility(payload: AssignPayload) -> dict:
    url = f"{BUK.base_url}/api/v1/chile/assigns"
    body = {
        "employee_id": payload.employee_id,
        "item_id": payload.item_id,
        "start_date": payload.start_date.strftime("%Y-%m-%d"),
        "end_date": "",
        "description": payload.description,
        "amount": payload.amount,
        "advance_payment_day": 0,
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
