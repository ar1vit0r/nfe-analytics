-- Grain: (month, issuer UF, CFOP).
select
    dt.month_start,
    e.emit_uf,
    f.cfop,
    sum(f.v_prod) as v_prod,
    sum(f.icms_valor) as v_icms,
    sum(f.pis_valor) as v_pis,
    sum(f.cofins_valor) as v_cofins
from {{ ref('fct_nfe_item') }} f
join {{ ref('dim_emitente') }} e using (emit_cnpj)
join {{ ref('dim_date') }} dt on dt.date_key = f.date_key
group by 1, 2, 3
