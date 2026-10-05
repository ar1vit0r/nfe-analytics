"""Testes da carga no PostgreSQL. Exigem TEST_DATABASE_URL (marcador db)."""

import os
from pathlib import Path

import psycopg
import pytest

from nfe_analytics.generator import generate_batch
from nfe_analytics.load import init_schema, load_folder
from nfe_analytics.parser import NfeParseError, parse_file
from nfe_analytics.validate import validate

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL nao definida"
    ),
]


@pytest.fixture
def conn():
    with psycopg.connect(os.environ["TEST_DATABASE_URL"]) as c:
        init_schema(c)
        c.execute(
            "TRUNCATE raw.rejected_file, raw.nfe_item, raw.nfe_document, "
            "raw.load_batch RESTART IDENTITY CASCADE"
        )
        c.commit()
        yield c


def _count(conn: psycopg.Connection, table: str) -> int:
    return conn.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]


def _rejeitado(path: Path) -> bool:
    try:
        return bool(validate(parse_file(path)))
    except NfeParseError:
        return True


def test_carga_200_com_defeitos_e_recarga_idempotente(conn, tmp_path: Path):
    generate_batch(200, seed=42, out_dir=tmp_path, defect_rate=0.05)
    esperado_rejeitados = sum(_rejeitado(p) for p in tmp_path.glob("*.xml"))
    assert esperado_rejeitados > 0  # a fixture precisa exercitar a rejeicao

    r1 = load_folder(conn, tmp_path)
    assert r1.files_seen == 200
    assert r1.files_loaded + r1.files_rejected == 200
    assert r1.files_rejected == esperado_rejeitados
    assert _count(conn, "nfe_document") == r1.files_loaded
    assert _count(conn, "rejected_file") == r1.files_rejected

    itens = _count(conn, "nfe_item")
    r2 = load_folder(conn, tmp_path)
    assert r2.files_loaded == 0
    assert _count(conn, "nfe_document") == r1.files_loaded
    assert _count(conn, "nfe_item") == itens
    assert _count(conn, "load_batch") == 2
