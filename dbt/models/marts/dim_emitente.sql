-- One row per issuer CNPJ; name and UF come from the latest note.
select distinct on (emit_cnpj)
    emit_cnpj,
    emit_nome,
    emit_uf
from {{ ref('stg_nfe__documents') }}
order by emit_cnpj, dh_emi desc nulls last, chave desc
