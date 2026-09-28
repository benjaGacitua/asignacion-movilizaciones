"""Check mínimo: roles.yaml con varios items por cargo y fallback por defecto."""
import yaml

from src.config import RoleConfig, DEFAULT_ROLE, CONFIG_DIR
from src.config import load_roles
from src.main import resolve_role


def test_kam_tiene_movilizacion_y_desgaste():
    roles = load_roles()
    items = resolve_role("Key Account Manager", roles)
    assert [(i.item_id, i.amount, i.description) for i in items] == [
        (2108, 125000, "movilizacion_2"),
        (1746, 250000, "asignacion_desgaste"),
    ]


def test_cargo_no_listado_usa_default():
    assert resolve_role("Vendedor", load_roles()) == [DEFAULT_ROLE]


def test_acepta_dict_suelto(tmp_path, monkeypatch):
    # compat con roles.yaml de un solo item (formato antiguo)
    import src.config as cfg
    (tmp_path / "roles.yaml").write_text(
        yaml.safe_dump({"roles": {"X": {"item_id": 1, "amount": 2, "description": "d"}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    assert cfg.load_roles() == {"X": [RoleConfig(1, 2, "d")]}


if __name__ == "__main__":
    test_kam_tiene_movilizacion_y_desgaste()
    test_cargo_no_listado_usa_default()
    print("OK")
