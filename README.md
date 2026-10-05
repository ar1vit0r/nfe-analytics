# nfe-analytics

Synthetic NF-e (model 55) XML generator, parser, validator, PostgreSQL loader and dbt star-schema marts, with CI.

Status: in progress. No real fiscal data is used. The generator emits a simplified subset of the NF-e 4.00 layout, not validated against the official XSD, with valid access-key check digits and CNPJs.

## What works today

- `generator.py`: deterministic synthetic notes, with optional injected defects (bad key, wrong total, truncated XML)
- `parser.py`: XML to typed `Document` and `Item` dataclasses; every malformed input raises `NfeParseError`
- `validate.py`: coded rule violations (key check digit, CNPJs, totals within 0.01, future date, item sequence)
- `fiscal.py`: access-key and CNPJ check digits
- `load.py` and `schema.sql`: idempotent load into `raw.*` tables with a per-run audit batch; files that fail parsing, validation or column limits go to `raw.rejected_file` with the reason
- `cli.py`: `generate` and `load` commands
- `dbt/`: staging views, then `dim_emitente`, `dim_produto`, `dim_date`, `fct_nfe_item` and `mart_impostos_mensal` (ICMS, PIS, COFINS by month, issuer UF and CFOP), with key, relationship and accepted-value tests plus a fact-to-raw total reconciliation
- `.github/workflows/ci.yml`: Postgres service, `pytest`, load of 200 synthetic notes, `dbt build`

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

Then build the marts (needs the optional `dbt` extra, ideally in its own virtualenv):

```
pip install -e '.[dbt]'
mkdir -p ~/.dbt && cp dbt/profiles.yml.example ~/.dbt/profiles.yml
dbt build --project-dir dbt
```

Models land in the `analytics_staging` and `analytics_marts` schemas. The emission date is taken in `America/Sao_Paulo` time, not the database session's.

## Run the tests

```
python3 -m pytest -q
```

The load test is skipped unless `TEST_DATABASE_URL` is set. It truncates the `raw` tables, so point it at a scratch database:

```
TEST_DATABASE_URL=postgresql://nfe:nfe@localhost:5434/nfe python3 -m pytest -q tests/test_load.py
```

## Planned

A pipeline diagram, and optional IBS/CBS (tax reform) fields once the current layout note is checked.
