import logging
import os
import sys
from datetime import date

import requests

from .buk_api import AssignPayload, assign_mobility, has_mobility_assign
from .config import DEFAULT_ROLE, N8N_WEBHOOK_URL, STATE_FILE, load_roles
from .db import fetch_current_month_employees
from .state import StateManager

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


def run_and_return() -> dict:
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
        raise

    logger.info("Nuevos ingresos en el mes: %d", len(employees))

    sent = skipped = failed = already_processed = 0
    detail_rows: list[dict] = []

    for emp in employees:
        employee_id = int(emp["id"])
        name_role = emp.get("name_role") or ""
        active_since: date = emp["active_since"]

        if state.is_sent(employee_id, current_month):
            logger.debug("SKIP  employee_id=%-6s (ya procesado en ejecución anterior)", employee_id)
            already_processed += 1
            continue

        role_cfg = resolve_role(name_role, roles)

        if role_cfg.amount == 0:
            logger.info("SKIP  employee_id=%-6s cargo='%s' (excluido por configuración)", employee_id, name_role)
            state.mark_sent(employee_id, current_month, "excluded", f"cargo={name_role}")
            detail_rows.append({"employee_id": employee_id, "cargo": name_role, "estado": "omitido", "detalle": "cargo excluido"})
            skipped += 1
            continue

        try:
            already_assigned = has_mobility_assign(employee_id)
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            logger.error(
                "ERROR employee_id=%-6s no se pudo consultar assigns en Buk — HTTP %s: %s",
                employee_id,
                exc.response.status_code if exc.response is not None else "?",
                detail,
            )
            detail_rows.append({"employee_id": employee_id, "cargo": name_role, "estado": "error", "detalle": f"GET assigns falló: {detail}"})
            failed += 1
            continue

        if already_assigned:
            logger.info("SKIP  employee_id=%-6s cargo='%s' (asignación ya existe en Buk)", employee_id, name_role)
            state.mark_sent(employee_id, current_month, "already_in_buk", "item encontrado via GET assigns")
            detail_rows.append({"employee_id": employee_id, "cargo": name_role, "estado": "omitido", "detalle": "ya tiene movilización en Buk"})
            skipped += 1
            continue

        logger.info("CHECK employee_id=%-6s cargo='%s' — sin asignación previa, procediendo al POST", employee_id, name_role)

        assign_payload = AssignPayload(
            employee_id=employee_id,
            item_id=role_cfg.item_id,
            start_date=active_since.replace(day=1),
            description=role_cfg.description,
            amount=role_cfg.amount,
        )

        try:
            result = assign_mobility(assign_payload)
            state.mark_sent(employee_id, current_month, "success", str(result))
            logger.info("OK    employee_id=%-6s cargo='%s' monto=%s ingreso=%s", employee_id, name_role, role_cfg.amount, active_since)
            detail_rows.append({"employee_id": employee_id, "cargo": name_role, "estado": "enviado", "detalle": f"monto={role_cfg.amount}"})
            sent += 1
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            state.mark_sent(employee_id, current_month, "error", detail)
            logger.error("ERROR employee_id=%-6s cargo='%s' — HTTP %s: %s", employee_id, name_role, exc.response.status_code if exc.response is not None else "?", detail)
            detail_rows.append({"employee_id": employee_id, "cargo": name_role, "estado": "error", "detalle": detail})
            failed += 1
        except Exception as exc:
            logger.error("ERROR employee_id=%-6s error inesperado: %s", employee_id, exc)
            detail_rows.append({"employee_id": employee_id, "cargo": name_role, "estado": "error", "detalle": str(exc)})
            failed += 1

    logger.info("=" * 60)
    logger.info("Resumen: enviados=%d  omitidos=%d  errores=%d  (ya procesados mes=%d)", sent, skipped, failed, already_processed)
    logger.info("=" * 60)

    return {
        "mes": current_month,
        "resumen": {
            "enviados": sent,
            "omitidos": skipped,
            "errores": failed,
            "ya_procesados_mes": already_processed,
        },
        "detalle": detail_rows,
    }


def _notify_n8n(result: dict):
    if not N8N_WEBHOOK_URL:
        return
    try:
        r = requests.post(N8N_WEBHOOK_URL, json=result, timeout=15)
        r.raise_for_status()
        logger.info("Notificacion enviada a n8n (HTTP %s)", r.status_code)
    except Exception as exc:
        logger.warning("No se pudo notificar a n8n: %s", exc)


def run():
    try:
        result = run_and_return()
    except Exception:
        sys.exit(1)
    _notify_n8n(result)
    if result["resumen"]["errores"]:
        sys.exit(1)


if __name__ == "__main__":
    run()
