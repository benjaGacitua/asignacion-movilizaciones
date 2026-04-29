import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class SSHConfig:
    host: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    database: str
    username: str
    password: str


@dataclass(frozen=True)
class BukConfig:
    base_url: str
    api_key: str


@dataclass(frozen=True)
class RoleConfig:
    item_id: int
    amount: int
    description: str


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Variable de entorno requerida no definida: {key}")
    return value


SSH = SSHConfig(
    host=_require("SSH_HOST"),
    port=int(os.getenv("SSH_PORT", "22")),
    username=_require("SSH_USERNAME"),
    password=_require("SSH_PASSWORD"),
)

DB = DBConfig(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=_require("DB_NAME"),
    username=_require("DB_USERNAME"),
    password=_require("DB_PASSWORD"),
)

BUK = BukConfig(
    base_url=os.getenv("BUK_BASE_URL", "https://demo.buk.cl"),
    api_key=_require("BUK_API_KEY"),
)

DEFAULT_ROLE = RoleConfig(
    item_id=int(os.getenv("DEFAULT_ITEM_ID", "1751")),
    amount=int(os.getenv("DEFAULT_AMOUNT", "40000")),
    description=os.getenv("DEFAULT_DESCRIPTION", "movilizacion"),
)

STATE_FILE = Path(os.getenv("STATE_FILE", "data/sent_records.json"))
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "config"))


def load_roles() -> dict[str, RoleConfig]:
    roles_path = CONFIG_DIR / "roles.yaml"
    if not roles_path.exists():
        return {}
    with open(roles_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        name: RoleConfig(
            item_id=cfg["item_id"],
            amount=cfg["amount"],
            description=cfg["description"],
        )
        for name, cfg in (data.get("roles") or {}).items()
    }
