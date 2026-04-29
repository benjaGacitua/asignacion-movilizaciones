import logging
import sys
from datetime import date

import requests

from .buk_api import AssignPayload, assign_mobility
from .config import DEFAULT_ROLE, STATE_FILE, load_roles
from .db import fetch_current_month_employees
from .state import StateManager

import os

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def resolve_role(name_role: str, roles: dict):
    if name_role in roles:
        logger.debug("Cargo '%s' encontrado en roles especiales", name_role)
        return roles[name_role]
    return DEFAULT_ROLE


def run():
    today = date.today()
    current_month = today.strftime("%Y-%m")

    logger.info("=" * 60)
    logger.info("Proceso movilizaciones — mes %s", current_month)
    logger.info("=" * 60)

    roles = load_roles()
    if roles:
        logger.info("Cargos especiales cargados: %s", list(roles.keys()))

    state = StateManager(STATE_FILE)

    try:
        employees = fetch_current_month_employees()
    except Exception as exc:
        logger.error("Error al conectar con la base de datos: %s", exc)
        sys.exit(1)

    logger.info("Nuevos ingresos en el mes: %d", len(employees))

    sent = skipped = failed = 0

    for emp in employees:
        employee_id = int(emp["id"])
        name_role = emp.get("name_role") or ""
        active_since: date = emp["active_since"]

        if state.is_sent(employee_id, current_month):
            logger.info("SKIP  employee_id=%-6s (ya enviado este mes)", employee_id)
            skipped += 1
            continue

        role_cfg = resolve_role(name_role, roles)

        # Cargos con amount=0 están excluidos de movilización
        if role_cfg.amount == 0:
            logger.info("SKIP  employee_id=%-6s cargo='%s' (excluido por configuración)", employee_id, name_role)
            state.mark_sent(employee_id, current_month, "excluded", f"cargo={name_role}")
            skipped += 1
            continue

        payload = AssignPayload(
            employee_id=employee_id,
            item_id=role_cfg.item_id,
            start_date=active_since,
            description=role_cfg.description,
            amount=role_cfg.amount,
        )

        try:
            result = assign_mobility(payload)
            state.mark_sent(employee_id, current_month, "success", str(result))
            logger.info(
                "OK    employee_id=%-6s cargo='%s' monto=%s ingreso=%s",
                employee_id, name_role, role_cfg.amount, active_since,
            )
            sent += 1
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            state.mark_sent(employee_id, current_month, "error", detail)
            logger.error(
                "ERROR employee_id=%-6s cargo='%s' — HTTP %s: %s",
                employee_id, name_role, exc.response.status_code if exc.response is not None else "?", detail,
            )
            failed += 1
        except Exception as exc:
            logger.error("ERROR employee_id=%-6s error inesperado: %s", employee_id, exc)
            failed += 1

    logger.info("=" * 60)
    logger.info("Resumen: enviados=%d  omitidos=%d  errores=%d", sent, skipped, failed)
    logger.info("=" * 60)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run()
