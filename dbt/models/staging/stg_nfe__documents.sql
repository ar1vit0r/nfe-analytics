select
    trim(chave) as chave,
    numero,
    serie,
    dh_emi,
    (dh_emi at time zone 'America/Sao_Paulo')::date as emission_date,  -- fiscal date is local, not the session's UTC
    trim(emit_cnpj) as emit_cnpj,
    emit_nome,
    trim(emit_uf) as emit_uf,
    trim(dest_cnpj) as dest_cnpj,
    dest_nome,
    trim(dest_uf) as dest_uf,
    v_prod,
    v_nf,
    v_bc,
    v_icms,
    v_pis,
    v_cofins
from {{ source('raw', 'nfe_document') }}
