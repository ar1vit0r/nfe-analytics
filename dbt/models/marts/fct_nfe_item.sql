select
    i.item_key,
    i.chave,
    i.n_item,
    d.emit_cnpj,
    i.product_key,
    d.emission_date as date_key,
    i.cfop,
    i.icms_cst,
    i.q_com,
    i.v_prod,
    i.icms_v_bc,
    i.icms_aliq,
    i.icms_valor,
    i.pis_valor,
    i.cofins_valor
from {{ ref('stg_nfe__items') }} i
join {{ ref('stg_nfe__documents') }} d using (chave)
