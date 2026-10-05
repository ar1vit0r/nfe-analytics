# nfe-analytics

Synthetic NF-e (model 55) XML generator, parser, validator and PostgreSQL loader. The dbt marts are next.

Status: in progress. No real fiscal data is used. The generator emits a simplified subset of the NF-e 4.00 layout, not validated against the official XSD, with valid access-key check digits and CNPJs.

## What works today

- `generator.py`: deterministic synthetic notes, with optional injected defects (bad key, wrong total, truncated XML)
- `parser.py`: XML to typed `Document` and `Item` dataclasses; every malformed input raises `NfeParseError`
- `validate.py`: coded rule violations (key check digit, CNPJs, totals within 0.01, future date, item sequence)
- `fiscal.py`: access-key and CNPJ check digits
- `load.py` and `schema.sql`: idempotent load into `raw.*` tables with a per-run audit batch; files that fail parsing, validation or column limits go to `raw.rejected_file` with the reason
- `cli.py`: `generate` and `load` commands

## Known simplifications

- ICMS groups 00, 20 and 40 only; PIS and COFINS with rate only
- `vNF = vProd` (no discount, freight or insurance); recipients identified by CNPJ only
- Load: a file whose access key already exists is skipped without a trace, and rejected files are logged again on every reload; amounts are stored as `NUMERIC(15,2)`

## Quick start

```
docker compose up -d --wait
python3 -m nfe_analytics.cli generate --n 200 --seed 42 --defect-rate 0.05
python3 -m nfe_analytics.cli load data/xml
```

The database URL comes from `--database-url` or `DATABASE_URL`, defaulting to the compose service on port 5434.

## Run the tests

```
python3 -m pytest -q
```

The load test is skipped unless `TEST_DATABASE_URL` is set. It truncates the `raw` tables, so point it at a scratch database:

```
TEST_DATABASE_URL=postgresql://nfe:nfe@localhost:5434/nfe python3 -m pytest -q tests/test_load.py
```

## Planned

dbt staging and marts (star schema, monthly tax report), dbt tests and CI.
