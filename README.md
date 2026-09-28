# nfe-analytics

Synthetic NF-e (model 55) XML generator, parser and validator. The PostgreSQL load and dbt marts are next.

Status: in progress. No real fiscal data is used. The generator emits a simplified subset of the NF-e 4.00 layout, not validated against the official XSD, with valid access-key check digits and CNPJs.

## What works today

- `generator.py`: deterministic synthetic notes, with optional injected defects (bad key, wrong total, truncated XML)
- `parser.py`: XML to typed `Document` and `Item` dataclasses; every malformed input raises `NfeParseError`
- `validate.py`: coded rule violations (key check digit, CNPJs, totals within 0.01, future date, item sequence)
- `fiscal.py`: access-key and CNPJ check digits

## Known simplifications

- ICMS groups 00, 20 and 40 only; PIS and COFINS with rate only
- `vNF = vProd` (no discount, freight or insurance); recipients identified by CNPJ only

## Run the tests

```
python3 -m pytest -q
```

## Planned

Load `raw` tables with a load audit trail, then dbt staging and marts (star schema, monthly tax report), dbt tests and CI.
