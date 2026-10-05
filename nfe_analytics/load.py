"""Carga de XMLs de NF-e no schema raw do PostgreSQL, com trilha de auditoria."""

import hashlib
import pathlib
from dataclasses import dataclass

import psycopg

from nfe_analytics.parser import Document, NfeParseError, parse_file
from nfe_analytics.validate import validate

SCHEMA_SQL = pathlib.Path(__file__).with_name("schema.sql")

_DOC_COLS = (
    "chave", "xml_sha256", "numero", "serie", "dh_emi", "emit_cnpj", "emit_nome",
    "emit_uf", "dest_cnpj", "dest_nome", "dest_uf", "v_prod", "v_nf", "v_bc",
    "v_icms", "v_pis", "v_cofins",
)
_ITEM_COLS = (
    "n_item", "c_prod", "x_prod", "ncm", "cfop", "u_com", "q_com", "v_un_com",
    "v_prod", "icms_cst", "icms_v_bc", "icms_aliq", "icms_valor", "pis_valor",
    "cofins_valor",
)

_INSERT_DOC = (
    f"INSERT INTO raw.nfe_document (batch_id, {', '.join(_DOC_COLS)}) "
    f"VALUES (%s{', %s' * len(_DOC_COLS)}) ON CONFLICT (chave) DO NOTHING"
)
_INSERT_ITEM = (
    f"INSERT INTO raw.nfe_item (chave, {', '.join(_ITEM_COLS)}) "
    f"VALUES (%s{', %s' * len(_ITEM_COLS)})"
)


@dataclass(frozen=True)
class BatchResult:
    batch_id: int
    files_seen: int
    files_loaded: int
    files_rejected: int


def init_schema(conn: psycopg.Connection) -> None:
    """Cria o schema raw (idempotente)."""
    conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    conn.commit()


def _insert_document(
    conn: psycopg.Connection, batch_id: int, doc: Document, sha256: str
) -> bool:
    """Insere nota e itens. Retorna False se a chave ja existia (nada e gravado)."""
    values = {**vars(doc), "xml_sha256": sha256}
    cur = conn.execute(
        _INSERT_DOC, (batch_id, *(values[c] for c in _DOC_COLS))
    )
    if cur.rowcount == 0:
        return False
    conn.cursor().executemany(
        _INSERT_ITEM,
        [(doc.chave, *(getattr(i, c) for c in _ITEM_COLS)) for i in doc.itens],
    )
    return True


def _reject(
    conn: psycopg.Connection, batch_id: int, file_name: str, sha256: str, reason: str
) -> None:
    conn.execute(
        "INSERT INTO raw.rejected_file (batch_id, file_name, xml_sha256, reason) "
        "VALUES (%s, %s, %s, %s)",
        (batch_id, file_name, sha256, reason),
    )


def load_folder(conn: psycopg.Connection, folder: pathlib.Path) -> BatchResult:
    """Carrega todos os *.xml de folder em um lote auditado.

    Arquivos que nao parseiam ou violam regras de validate() vao para
    raw.rejected_file. Notas cuja chave ja existe sao ignoradas (recarregar a
    mesma pasta carrega 0).
    """
    batch_id: int = conn.execute(
        "INSERT INTO raw.load_batch DEFAULT VALUES RETURNING batch_id"
    ).fetchone()[0]
    seen = loaded = rejected = 0

    for path in sorted(folder.glob("*.xml")):
        seen += 1
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            doc = parse_file(path)
            erros = validate(doc)
            reason = "; ".join(erros) if erros else None
        except NfeParseError as e:
            doc, reason = None, f"parse: {e}"

        if reason is not None:
            rejected += 1
            _reject(conn, batch_id, path.name, sha256, reason)
        else:
            try:
                with conn.transaction():  # savepoint: a bad file must not abort the batch
                    inserted = _insert_document(conn, batch_id, doc, sha256)
            except (psycopg.DataError, psycopg.IntegrityError) as e:
                rejected += 1
                _reject(conn, batch_id, path.name, sha256, f"db: {e}")
            else:
                loaded += inserted

    conn.execute(
        "UPDATE raw.load_batch SET finished_at = now(), files_seen = %s, "
        "files_loaded = %s, files_rejected = %s WHERE batch_id = %s",
        (seen, loaded, rejected, batch_id),
    )
    conn.commit()
    return BatchResult(batch_id, seen, loaded, rejected)
