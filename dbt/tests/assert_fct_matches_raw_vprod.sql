-- Returns rows (= failure) where the item sum in the fact differs from the raw note total.
select
    d.chave,
    d.v_prod as raw_v_prod,
    coalesce(sum(f.v_prod), 0) as fct_v_prod
from {{ source('raw', 'nfe_document') }} d
left join {{ ref('fct_nfe_item') }} f on f.chave = trim(d.chave)
group by d.chave, d.v_prod
having abs(coalesce(sum(f.v_prod), 0) - d.v_prod) > 0.01
