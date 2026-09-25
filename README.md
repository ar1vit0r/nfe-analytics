# nfe-analytics

Synthetic NF-e (model 55, layout 4.00) XML files loaded into PostgreSQL and modeled with dbt.

Status: in progress. No real fiscal data is used: the XML files come from a generator that follows the public SEFAZ schema, with valid access-key check digits and CNPJs.

Planned pipeline: generate XML -> parse and validate -> load `raw` tables with a load audit trail -> dbt staging and marts (star schema, monthly tax report) -> dbt tests and CI.
