CREATE TABLE public.pncp_coletas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    data_inicio TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_fim TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'EM_ANDAMENTO',
    quantidade_atas INTEGER DEFAULT 0,

    CONSTRAINT chk_periodo_coleta
        CHECK (periodo_fim >= periodo_inicio),

    CONSTRAINT chk_status_coleta
        CHECK (status IN ('EM_ANDAMENTO', 'CONCLUIDA', 'ERRO'))
);


CREATE TABLE public.stg_pncp_registros (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    coleta_id BIGINT NOT NULL,
    numero_controle_pncp_ata VARCHAR(100) NOT NULL,
    dados_originais JSONB NOT NULL,
    data_coleta TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_stg_coleta_ata
        UNIQUE (coleta_id, numero_controle_pncp_ata),

    CONSTRAINT fk_stg_coleta
        FOREIGN KEY (coleta_id)
        REFERENCES public.pncp_coletas(id)
);




CREATE TABLE public.pncp_atas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    numero_controle_pncp_ata VARCHAR(100) NOT NULL,
    numero_ata_registro_preco VARCHAR(100),
    ano_ata INTEGER,
    numero_controle_pncp_compra VARCHAR(100),
    cnpj_orgao VARCHAR(14),
    nome_orgao VARCHAR(255),
    objeto_contratacao TEXT,
    cancelado BOOLEAN,
    data_cancelamento DATE,
    data_assinatura DATE,
    vigencia_inicio DATE,
    vigencia_fim DATE,
    data_publicacao_pncp TIMESTAMP,
    data_inclusao_pncp TIMESTAMP,
    data_atualizacao_pncp TIMESTAMP,
    ultima_coleta_id BIGINT,
    data_coleta TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pncp_atas_numero_controle_pncp_ata_key
        UNIQUE (numero_controle_pncp_ata),

    CONSTRAINT pncp_atas_ultima_coleta_id_fkey
        FOREIGN KEY (ultima_coleta_id)
        REFERENCES public.pncp_coletas(id)
);



CREATE TABLE public.pncp_itens (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ata_id BIGINT NOT NULL,
    numero_item INTEGER NOT NULL,
    descricao TEXT,
    material_ou_servico VARCHAR(10),
    valor_unitario_estimado NUMERIC(18,4),
    valor_total NUMERIC(18,4),
    quantidade NUMERIC(18,4),
    unidade_medida VARCHAR(100),
    situacao_compra_item INTEGER,
    situacao_compra_item_nome VARCHAR(100),
    tem_resultado BOOLEAN,
    data_inclusao_pncp TIMESTAMP,
    data_atualizacao_pncp TIMESTAMP,
    ultima_coleta_id BIGINT,
    data_coleta TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_item_ata
        UNIQUE (ata_id, numero_item),

    CONSTRAINT fk_item_ata
        FOREIGN KEY (ata_id)
        REFERENCES public.pncp_atas(id),

    CONSTRAINT pncp_itens_ultima_coleta_id_fkey
        FOREIGN KEY (ultima_coleta_id)
        REFERENCES public.pncp_coletas(id)
);


CREATE TABLE public.pncp_resultados (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id BIGINT NOT NULL,
    sequencial_resultado INTEGER NOT NULL,
    ni_fornecedor VARCHAR(20),
    tipo_pessoa VARCHAR(10),
    nome_razao_social_fornecedor VARCHAR(255),
    valor_total_homologado NUMERIC(18,4),
    valor_unitario_homologado NUMERIC(18,4),
    quantidade_homologada NUMERIC(18,4),
    percentual_desconto NUMERIC(18,4),
    data_resultado DATE,
    data_cancelamento DATE,
    data_inclusao_pncp TIMESTAMP,
    data_atualizacao_pncp TIMESTAMP,
    ultima_coleta_id BIGINT,
    data_coleta TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_resultado_item
        UNIQUE (item_id, sequencial_resultado),

    CONSTRAINT fk_resultado_item
        FOREIGN KEY (item_id)
        REFERENCES public.pncp_itens(id),

    CONSTRAINT pncp_resultados_ultima_coleta_id_fkey
        FOREIGN KEY (ultima_coleta_id)
        REFERENCES public.pncp_coletas(id)
);



SELECT
    conrelid::regclass AS tabela,
    conname AS restricao,
    CASE contype
        WHEN 'p' THEN 'PRIMARY KEY'
        WHEN 'f' THEN 'FOREIGN KEY'
        WHEN 'u' THEN 'UNIQUE'
        WHEN 'c' THEN 'CHECK'
    END AS tipo,
    pg_get_constraintdef(oid) AS definicao
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, contype, conname;


