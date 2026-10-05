-- One row per day between the first and last emission date.
select
    d::date as date_key,
    extract(year from d)::int as year,
    extract(month from d)::int as month,
    date_trunc('month', d)::date as month_start
from (
    select generate_series(min(emission_date), max(emission_date), interval '1 day') as d
    from {{ ref('stg_nfe__documents') }}
) days
