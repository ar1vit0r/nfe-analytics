-- One row per (c_prod, ncm); description and unit come from the first item seen.
select distinct on (c_prod, ncm)
    product_key,
    c_prod,
    ncm,
    x_prod,
    u_com
from {{ ref('stg_nfe__items') }}
order by c_prod, ncm, item_key
