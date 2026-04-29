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


def assign_mobility(payload: AssignPayload) -> dict:
    url = f"{BUK.base_url}/api/v1/chile/assigns"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {BUK.api_key}",
    }
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
    response = _SESSION.post(url, headers=headers, json=body, timeout=30)
    response.raise_for_status()
    return response.json()
