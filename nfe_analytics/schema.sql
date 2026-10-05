-- Schema raw: escrito apenas pelo load.py. Idempotente (IF NOT EXISTS).
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.load_batch (
    batch_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    files_seen     INTEGER NOT NULL DEFAULT 0,
    files_loaded   INTEGER NOT NULL DEFAULT 0,
    files_rejected INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS raw.nfe_document (
    chave      CHAR(44) PRIMARY KEY,
    batch_id   BIGINT NOT NULL REFERENCES raw.load_batch (batch_id),
    xml_sha256 CHAR(64) NOT NULL,
    numero     INTEGER NOT NULL,
    serie      INTEGER NOT NULL,
    dh_emi     TIMESTAMPTZ NOT NULL,
    emit_cnpj  CHAR(14) NOT NULL,
    emit_nome  TEXT NOT NULL,
    emit_uf    CHAR(2) NOT NULL,
    dest_cnpj  CHAR(14) NOT NULL,
    dest_nome  TEXT NOT NULL,
    dest_uf    CHAR(2) NOT NULL,
    v_prod     NUMERIC(15, 2) NOT NULL,
    v_nf       NUMERIC(15, 2) NOT NULL,
    v_bc       NUMERIC(15, 2) NOT NULL,
    v_icms     NUMERIC(15, 2) NOT NULL,
    v_pis      NUMERIC(15, 2) NOT NULL,
    v_cofins   NUMERIC(15, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.nfe_item (
    chave        CHAR(44) NOT NULL REFERENCES raw.nfe_document (chave),
    n_item       INTEGER NOT NULL,
    c_prod       TEXT NOT NULL,
    x_prod       TEXT NOT NULL,
    ncm          CHAR(8) NOT NULL,
    cfop         CHAR(4) NOT NULL,
    u_com        TEXT NOT NULL,
    q_com        NUMERIC(15, 4) NOT NULL,
    v_un_com     NUMERIC(21, 10) NOT NULL,
    v_prod       NUMERIC(15, 2) NOT NULL,
    icms_cst     CHAR(2) NOT NULL,
    icms_v_bc    NUMERIC(15, 2),
    icms_aliq    NUMERIC(7, 4),
    icms_valor   NUMERIC(15, 2) NOT NULL,
    pis_valor    NUMERIC(15, 2) NOT NULL,
    cofins_valor NUMERIC(15, 2) NOT NULL,
    PRIMARY KEY (chave, n_item)
);

CREATE TABLE IF NOT EXISTS raw.rejected_file (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id    BIGINT NOT NULL REFERENCES raw.load_batch (batch_id),
    file_name   TEXT NOT NULL,
    xml_sha256  CHAR(64) NOT NULL,
    reason      TEXT NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
