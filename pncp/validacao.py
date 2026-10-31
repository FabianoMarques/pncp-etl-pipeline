import logging

logger = logging.getLogger(__name__)

CAMPO_IDENTIFICADOR = "numeroControlePNCPAta"
CAMPO_CANCELADO = "cancelado"


def validar_registros(registros: list[dict]) -> list[dict]:
    if not isinstance(registros, list):
        raise TypeError("A entrada deve ser uma lista de registros.")

    if not registros:
        raise ValueError("Nenhum registro foi recebido para validação.")

    erros = []
    identificadores = set()

    for indice, registro in enumerate(registros, start=1):
        if not isinstance(registro, dict):
            erros.append(f"Registro {indice}: formato inválido.")
            continue

        identificador = registro.get(CAMPO_IDENTIFICADOR)

        if not isinstance(identificador, str) or not identificador.strip():
            erros.append(
                f"Registro {indice}: identificador ausente ou inválido."
            )
            continue

        if CAMPO_CANCELADO not in registro:
            erros.append(
                f"Registro {indice}: campo 'cancelado' ausente."
            )
            continue

        if not isinstance(registro[CAMPO_CANCELADO], bool):
            erros.append(
                f"Registro {indice}: campo 'cancelado' deve ser booleano."
            )
            continue

        if identificador in identificadores:
            erros.append(
                f"Registro {indice}: identificador duplicado '{identificador}'."
            )
            continue

        identificadores.add(identificador)

    if erros:
        for erro in erros:
            logger.error(erro)

        raise ValueError(
            f"Validação reprovada: {len(erros)} inconsistência(s) encontrada(s)."
        )

    logger.info(
        "Validação concluída: %s registros aprovados.",
        len(registros),
    )

    return registros

def gerar_relatorio_ausencias(
    dataframes: dict,
    arquivo_origem: str,
    caminho_saida: str = "dados/relatorio_qualidade_pncp.csv",
) -> None:
    """
    Gera um relatório CSV dos campos com valores ausentes,
    incluindo classificação e justificativa técnica.
    """

    import pandas as pd
    from datetime import datetime
    from pathlib import Path

    classificacoes = {
        ("df_atas", "data_cancelamento"): {
            "classificacao": "Ausência compatível com a situação observada",
            "observacao": (
                "Na amostra, todos os registros estão com cancelado=False "
                "e sem data de cancelamento."
            ),
        },
        ("df_atas", "cnpj_orgao_subrogado"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os registros analisados.",
        },
        ("df_atas", "nome_orgao_subrogado"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os registros analisados.",
        },
        ("df_atas", "codigo_unidade_orgao_subrogado"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os registros analisados.",
        },
        ("df_atas", "nome_unidade_orgao_subrogado"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os registros analisados.",
        },
        ("df_atas", "possibilidade_adesao"): {
            "classificacao": "Ausência parcial",
            "observacao": (
                "Campo preenchido em parte dos registros. "
                "Os valores ausentes foram preservados como não informados."
            ),
        },

        ("df_itens", "patrimonio"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens analisados.",
        },
        ("df_itens", "codigo_registro_imobiliario"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens analisados.",
        },
        ("df_itens", "percentual_margem_preferencia_normal"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens analisados.",
        },
        ("df_itens", "percentual_margem_preferencia_adicional"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens analisados.",
        },
        ("df_itens", "ncm_nbs_codigo"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": (
                "Campo ausente em todos os itens, incluindo materiais e serviços."
            ),
        },
        ("df_itens", "ncm_nbs_descricao"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens analisados.",
        },
        ("df_itens", "catalogo"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens, incluindo materiais e serviços.",
        },
        ("df_itens", "categoria_item_catalogo"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens analisados.",
        },
        ("df_itens", "catalogo_codigo_item"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens, incluindo materiais e serviços.",
        },
        ("df_itens", "informacao_complementar"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens analisados.",
        },
        ("df_itens", "tipo_margem_preferencia"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os itens analisados.",
        },

        ("df_resultados", "data_cancelamento"): {
            "classificacao": "Ausência compatível com a situação observada",
            "observacao": (
                "Na amostra, os resultados estão com situação "
                "'Informado' e sem data de cancelamento."
            ),
        },
        ("df_resultados", "motivo_cancelamento"): {
            "classificacao": "Ausência compatível com a situação observada",
            "observacao": (
                "Na amostra, os resultados estão com situação "
                "'Informado' e sem motivo de cancelamento."
            ),
        },
        ("df_resultados", "timezone_cotacao_moeda_estrangeira"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
        ("df_resultados", "moeda_estrangeira"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
        ("df_resultados", "valor_nominal_moeda_estrangeira"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
        ("df_resultados", "data_cotacao_moeda_estrangeira"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
        ("df_resultados", "natureza_juridica_id"): {
            "classificacao": "Informação parcialmente fornecida",
            "observacao": (
                "Campo preenchido em parte dos resultados. "
                "Os registros sem informação não tiveram o valor inferido."
            ),
        },
        ("df_resultados", "natureza_juridica_nome"): {
            "classificacao": "Informação parcialmente fornecida",
            "observacao": (
                "Campo preenchido em parte dos resultados. "
                "A ausência ocorre junto com a ausência do identificador."
            ),
        },
        ("df_resultados", "amparo_legal_margem_preferencia"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
        ("df_resultados", "amparo_legal_criterio_desempate"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
        ("df_resultados", "pais_origem_produto_servico"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
        ("df_resultados", "localidade_exterior"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
        ("df_resultados", "localidade_fornecedor"): {
            "classificacao": "Informação não fornecida na amostra",
            "observacao": "Campo ausente em todos os resultados analisados.",
        },
    }

    registros = []
    data_execucao = datetime.now().isoformat(timespec="seconds")

    for nome_dataframe, df in dataframes.items():
        total_registros = len(df)

        for campo in df.columns:
            ausentes = int(df[campo].isna().sum())

            if ausentes == 0:
                continue

            percentual = (
                (ausentes / total_registros) * 100
                if total_registros > 0
                else 0
            )

            classificacao = classificacoes.get(
                (nome_dataframe, campo),
                {
                    "classificacao": "Pendente de classificação",
                    "observacao": "Campo ainda não possui regra de classificação definida.",
                },
            )

            registros.append({
                "data_execucao": data_execucao,
                "arquivo_origem": arquivo_origem,
                "dataframe": nome_dataframe,
                "campo": campo,
                "total_registros": total_registros,
                "valores_ausentes": ausentes,
                "percentual_ausencia": round(percentual, 2),
                "classificacao": classificacao["classificacao"],
                "decisao": "Preservar os valores ausentes, sem preenchimento automático.",
                "observacao": classificacao["observacao"],
            })

    colunas = [
        "data_execucao",
        "arquivo_origem",
        "dataframe",
        "campo",
        "total_registros",
        "valores_ausentes",
        "percentual_ausencia",
        "classificacao",
        "decisao",
        "observacao",
    ]

    relatorio = pd.DataFrame(registros, columns=colunas)

    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    relatorio.to_csv(
        caminho,
        index=False,
        encoding="utf-8-sig",
        sep=";",
    )

    logger.info(
        "Relatório de qualidade gerado: %s (%s campos com ausência).",
        caminho,
        len(relatorio),
    )


def validar_dataframes(df_atas, df_itens, df_resultados):
    import re
    import numpy as np
    import pandas as pd

    erros = []
    alertas = []

    # 1. Verificar identificadores obrigatórios
    if df_atas["numeroControlePNCPAta"].isna().any():
        erros.append("Existem atas sem identificador.")

    if df_itens["numeroControlePNCPAta"].isna().any():
        erros.append("Existem itens sem identificador da ata.")

    if df_resultados["numeroControlePNCPAta"].isna().any():
        erros.append("Existem resultados sem identificador da ata.")

    # 2. Verificar duplicidade das chaves
    if df_atas.duplicated(["numeroControlePNCPAta"]).any():
        erros.append("Existem atas duplicadas.")

    if df_itens.duplicated(
        ["numeroControlePNCPAta", "numeroItem"]
    ).any():
        erros.append("Existem itens com chaves duplicadas.")

    if df_resultados.duplicated(
        ["numeroControlePNCPAta", "numeroItem", "sequencialResultado"]
    ).any():
        erros.append("Existem resultados com chaves duplicadas.")

    # 3. Verificar formato dos identificadores das atas
    padrao = r"^\d{14}-\d-\d{6}/\d{4}-\d{6}$"

    invalidos = ~df_atas["numeroControlePNCPAta"].apply(
        lambda valor: isinstance(valor, str)
        and bool(re.fullmatch(padrao, valor))
    )

    if invalidos.any():
        erros.append(
            f"Existem {invalidos.sum()} identificadores de ata fora do padrão."
        )

    # 4. Verificar relacionamentos
    chaves_atas = set(df_atas["numeroControlePNCPAta"].dropna())

    chaves_itens = set(df_itens["numeroControlePNCPAta"].dropna())

    chaves_resultados = set(
        df_resultados["numeroControlePNCPAta"].dropna()
    )

    if not chaves_itens.issubset(chaves_atas):
        erros.append("Existem itens sem ata correspondente.")

    if not chaves_resultados.issubset(chaves_atas):
        erros.append("Existem resultados sem ata correspondente.")

    chaves_itens_completas = set(
        zip(
            df_itens["numeroControlePNCPAta"],
            df_itens["numeroItem"],
        )
    )

    chaves_resultados_itens = set(
        zip(
            df_resultados["numeroControlePNCPAta"],
            df_resultados["numeroItemOrigem"],
        )
    )

    if not chaves_resultados_itens.issubset(chaves_itens_completas):
        erros.append("Existem resultados sem item correspondente.")

    # 5. Verificar identificadores inteiros positivos
    campos_inteiros = {
        "itens.numeroItem": df_itens["numeroItem"],
        "resultados.numeroItem": df_resultados["numeroItem"],
        "resultados.sequencialResultado": df_resultados[
            "sequencialResultado"
        ],
    }

    for nome, serie in campos_inteiros.items():

        if not pd.api.types.is_integer_dtype(serie.dtype):
            erros.append(f"{nome} não possui tipo inteiro.")

        if serie.isna().any() or (serie <= 0).any():
            erros.append(f"{nome} possui valores ausentes ou não positivos.")

    # 6. Verificar consistência entre item e resultado
    divergencias = (
        df_resultados["numeroItem"]
        != df_resultados["numeroItemOrigem"]
    )

    if divergencias.any():
        erros.append(
            f"Existem {divergencias.sum()} resultados com número de item divergente."
        )

    # 7. Verificar valores negativos
    campos_numericos = {
        "itens.valorUnitarioEstimado": df_itens["valorUnitarioEstimado"],
        "itens.valorTotal": df_itens["valorTotal"],
        "itens.quantidade": df_itens["quantidade"],
        "resultados.valorUnitarioHomologado": df_resultados[
            "valorUnitarioHomologado"
        ],
        "resultados.valorTotalHomologado": df_resultados[
            "valorTotalHomologado"
        ],
        "resultados.quantidadeHomologada": df_resultados[
            "quantidadeHomologada"
        ],
        "resultados.percentualDesconto": df_resultados[
            "percentualDesconto"
        ],
    }

    for nome, serie in campos_numericos.items():

        if not pd.api.types.is_numeric_dtype(serie.dtype):
            erros.append(f"{nome} não possui tipo numérico.")
            continue

        if (serie.dropna() < 0).any():
            erros.append(f"{nome} possui valores negativos.")

    # 8. Verificar percentual de desconto
    percentual = df_resultados["percentualDesconto"]

    if ((percentual < 0) | (percentual > 100)).any():
        erros.append("Existem percentuais de desconto fora do intervalo de 0 a 100.")

    # 9. Verificar consistência aritmética
    calculado_itens = (
        df_itens["valorUnitarioEstimado"] * df_itens["quantidade"]
    )

    divergencias_itens = ~np.isclose(
        calculado_itens,
        df_itens["valorTotal"],
        rtol=1e-5,
        atol=0.01,
    )

    if divergencias_itens.any():
        erros.append(
            f"Existem {divergencias_itens.sum()} divergências nos valores totais dos itens."
        )

    calculado_resultados = (
        df_resultados["valorUnitarioHomologado"]
        * df_resultados["quantidadeHomologada"]
    )

    divergencias_resultados = ~np.isclose(
        calculado_resultados,
        df_resultados["valorTotalHomologado"],
        rtol=1e-5,
        atol=0.01,
    )

    if divergencias_resultados.any():
        erros.append(
            f"Existem {divergencias_resultados.sum()} divergências nos valores homologados."
        )

    # 10. Registrar alertas de qualidade
    itens_zerados = (
        (df_itens["valorUnitarioEstimado"] == 0)
        | (df_itens["valorTotal"] == 0)
    ).sum()

    if itens_zerados:
        alertas.append(
            f"{itens_zerados} itens possuem valores estimados zerados."
        )

    # Resultado da validação
    for erro in erros:
        logger.error(erro)

    for alerta in alertas:
        logger.warning(alerta)

    if erros:
        raise ValueError(
            f"Validação reprovada: {len(erros)} inconsistência(s)."
        )

    logger.info(
        "Validação aprovada: %s atas, %s itens e %s resultados.",
        len(df_atas),
        len(df_itens),
        len(df_resultados),
    )

    return {
        "status": "aprovado",
        "total_erros": len(erros),
        "total_alertas": len(alertas),
        "alertas": alertas,
    }


def separar_atas_invalidas(df_atas):
    import re
    import numpy as np
    import pandas as pd

    padrao = r"^\d{14}-\d-\d{6}/\d{4}-\d{6}$"

    motivos = {}

    # Identificar identificadores duplicados
    duplicados = df_atas[
        "numeroControlePNCPAta"
    ].duplicated(keep=False)

    for indice in df_atas.index:

        registro = df_atas.loc[indice]
        erros = []

        identificador = registro["numeroControlePNCPAta"]

        # 1. Validar identificador
        if (
            not isinstance(identificador, str)
            or not identificador.strip()
        ):
            erros.append("Identificador ausente ou inválido.")

        elif not re.fullmatch(padrao, identificador):
            erros.append("Identificador fora do padrão esperado.")

        # 2. Validar campo cancelado
        cancelado = registro["cancelado"]

        if pd.isna(cancelado):
            erros.append("Campo cancelado ausente.")

        elif not isinstance(cancelado, (bool, np.bool_)):
            erros.append("Campo cancelado deve ser booleano.")

        # 3. Validar duplicidade
        if duplicados.loc[indice]:
            erros.append("Identificador de ata duplicado.")

        if erros:
            motivos[indice] = erros

    # Separar registros
    df_invalidas = df_atas.loc[list(motivos)].copy()

    df_validas = df_atas.drop(
        index=list(motivos)
    ).copy()

    # Registrar os motivos nas atas inválidas
    if not df_invalidas.empty:
        df_invalidas["motivos_invalidade"] = [
            "; ".join(motivos[indice])
            for indice in df_invalidas.index
        ]

    # Criar relatório detalhado
    registros_relatorio = []

    for indice, erros in motivos.items():
        for erro in erros:
            registros_relatorio.append({
                "indice_origem": indice,
                "numeroControlePNCPAta": df_atas.loc[
                    indice, "numeroControlePNCPAta"
                ],
                "motivo": erro,
            })

    relatorio = pd.DataFrame(
        registros_relatorio,
        columns=[
            "indice_origem",
            "numeroControlePNCPAta",
            "motivo",
        ],
    )

    logger.info(
        "Validação individual das atas: %s válidas e %s inválidas.",
        len(df_validas),
        len(df_invalidas),
    )

    return df_validas, df_invalidas, relatorio


def separar_itens_invalidos(df_itens):
    import pandas as pd
    import numpy as np

    motivos = {}

    # Identificar duplicidades na chave composta
    duplicados = df_itens.duplicated(
        subset=["numeroControlePNCPAta", "numeroItem"],
        keep=False,
    )

    for indice in df_itens.index:

        registro = df_itens.loc[indice]
        erros = []

        identificador = registro["numeroControlePNCPAta"]
        numero_item = registro["numeroItem"]

        # 1. Validar identificador da ata
        if (
            not isinstance(identificador, str)
            or not identificador.strip()
        ):
            erros.append("Identificador da ata ausente ou inválido.")

        # 2. Validar número do item
        if pd.isna(numero_item):
            erros.append("Número do item ausente.")

        elif (
            isinstance(numero_item, (bool, np.bool_))
            or not isinstance(numero_item, (int, np.integer))
            or numero_item <= 0
        ):
            erros.append("Número do item deve ser um inteiro positivo.")

        # 3. Validar duplicidade da chave composta
        if duplicados.loc[indice]:
            erros.append("Chave composta do item duplicada.")

        if erros:
            motivos[indice] = erros

    # Separar registros
    df_invalidas = df_itens.loc[list(motivos)].copy()

    df_validas = df_itens.drop(
        index=list(motivos)
    ).copy()

    # Registrar motivos nos itens inválidos
    if not df_invalidas.empty:
        df_invalidas["motivos_invalidade"] = [
            "; ".join(motivos[indice])
            for indice in df_invalidas.index
        ]

    # Criar relatório detalhado
    registros_relatorio = []

    for indice, erros in motivos.items():
        for erro in erros:
            registros_relatorio.append({
                "indice_origem": indice,
                "numeroControlePNCPAta": df_itens.loc[
                    indice, "numeroControlePNCPAta"
                ],
                "numeroItem": df_itens.loc[indice, "numeroItem"],
                "motivo": erro,
            })

    relatorio = pd.DataFrame(
        registros_relatorio,
        columns=[
            "indice_origem",
            "numeroControlePNCPAta",
            "numeroItem",
            "motivo",
        ],
    )

    logger.info(
        "Validação individual dos itens: %s válidos e %s inválidos.",
        len(df_validas),
        len(df_invalidas),
    )

    return df_validas, df_invalidas, relatorio


def separar_resultados_invalidos(df_resultados):
    import pandas as pd
    import numpy as np

    motivos = {}

    # Identificar duplicidades na chave composta
    duplicados = df_resultados.duplicated(
        subset=[
            "numeroControlePNCPAta",
            "numeroItem",
            "sequencialResultado",
        ],
        keep=False,
    )

    for indice in df_resultados.index:

        registro = df_resultados.loc[indice]
        erros = []

        identificador = registro["numeroControlePNCPAta"]
        numero_item = registro["numeroItem"]
        numero_item_origem = registro["numeroItemOrigem"]
        sequencial = registro["sequencialResultado"]

        # 1. Validar identificador da ata
        if (
            not isinstance(identificador, str)
            or not identificador.strip()
        ):
            erros.append("Identificador da ata ausente ou inválido.")

        # 2. Validar número do item
        if pd.isna(numero_item):
            erros.append("Número do item ausente.")

        elif (
            isinstance(numero_item, (bool, np.bool_))
            or not isinstance(numero_item, (int, np.integer))
            or numero_item <= 0
        ):
            erros.append("Número do item deve ser um inteiro positivo.")

        # 3. Validar número do item de origem
        if pd.isna(numero_item_origem):
            erros.append("Número do item de origem ausente.")

        elif (
            isinstance(numero_item_origem, (bool, np.bool_))
            or not isinstance(numero_item_origem, (int, np.integer))
            or numero_item_origem <= 0
        ):
            erros.append(
                "Número do item de origem deve ser um inteiro positivo."
            )

        elif (
            isinstance(numero_item, (int, np.integer))
            and numero_item_origem != numero_item
        ):
            erros.append(
                "Número do item divergente do número do item de origem."
            )

        # 4. Validar sequencial do resultado
        if pd.isna(sequencial):
            erros.append("Sequencial do resultado ausente.")

        elif (
            isinstance(sequencial, (bool, np.bool_))
            or not isinstance(sequencial, (int, np.integer))
            or sequencial <= 0
        ):
            erros.append(
                "Sequencial do resultado deve ser um inteiro positivo."
            )

        # 5. Validar duplicidade da chave composta
        if duplicados.loc[indice]:
            erros.append("Chave composta do resultado duplicada.")

        if erros:
            motivos[indice] = erros

    # Separar registros
    df_invalidas = df_resultados.loc[list(motivos)].copy()

    df_validas = df_resultados.drop(
        index=list(motivos)
    ).copy()

    # Registrar motivos nos resultados inválidos
    if not df_invalidas.empty:
        df_invalidas["motivos_invalidade"] = [
            "; ".join(motivos[indice])
            for indice in df_invalidas.index
        ]

    # Criar relatório detalhado
    registros_relatorio = []

    for indice, erros in motivos.items():
        for erro in erros:
            registros_relatorio.append({
                "indice_origem": indice,
                "numeroControlePNCPAta": df_resultados.loc[
                    indice, "numeroControlePNCPAta"
                ],
                "numeroItem": df_resultados.loc[indice, "numeroItem"],
                "sequencialResultado": df_resultados.loc[
                    indice, "sequencialResultado"
                ],
                "motivo": erro,
            })

    relatorio = pd.DataFrame(
        registros_relatorio,
        columns=[
            "indice_origem",
            "numeroControlePNCPAta",
            "numeroItem",
            "sequencialResultado",
            "motivo",
        ],
    )

    logger.info(
        "Validação individual dos resultados: %s válidos e %s inválidos.",
        len(df_validas),
        len(df_invalidas),
    )

    return df_validas, df_invalidas, relatorio