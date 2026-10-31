import logging
from pathlib import Path
from datetime import datetime

from pncp.extracao import (
    extrair_atas,
    extrair_dados_complementares,
)

from pncp.transformacao import (
    criar_dataframes,
)

from pncp.validacao import (
    separar_atas_invalidas,
    separar_itens_invalidos,
    separar_resultados_invalidos,
    validar_dataframes,
)

from pncp.exportacao import exportar_json, exportar_csv


# Configuração dos parâmetros da extração.
DATA_INICIAL = "20261001"
DATA_FINAL = "20261028"
TAMANHO_PAGINA = 10
MAX_PAGINAS = 1 #None
TAMANHO_PAGINA_ITENS = 100


# Configuração dos logs.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def executar():

    logging.info("Iniciando extração do PNCP.")

    # 1. Extrair atas.
    atas = extrair_atas(
        data_inicial=DATA_INICIAL,
        data_final=DATA_FINAL,
        tamanho_pagina=TAMANHO_PAGINA,
        max_paginas=MAX_PAGINAS,
    )

    logging.info("Total de atas extraídas: %s", len(atas))

    # 2. Consultar dados complementares.
    dados = extrair_dados_complementares(
        atas=atas,
        tamanho_pagina_itens=TAMANHO_PAGINA_ITENS,
    )

    logging.info(
        "Total de atas com dados complementares processadas: %s",
        len(dados),
    )

    # 3. Preparar o arquivo JSON.
    pasta_saida = Path("dados")
    nome_arquivo = (
        f"dados_pncp_{DATA_INICIAL}_{DATA_FINAL}.json"
    )

    caminho_arquivo = pasta_saida / nome_arquivo

    # 4. Exportar os dados.
    exportar_json(
        dados=dados,
        caminho_arquivo=caminho_arquivo,
    )

    logging.info(
        "Arquivo JSON gerado: %s",
        caminho_arquivo,
    )

    # 5. Criar DataFrames para análise e validação.
    df_atas, df_itens, df_resultados = criar_dataframes(dados)

    # 6. Separar registros válidos e inválidos.
    _, _, relatorio_atas = separar_atas_invalidas(df_atas)

    _, _, relatorio_itens = separar_itens_invalidos(df_itens)

    _, _, relatorio_resultados = separar_resultados_invalidos(df_resultados)

    # 7. Exportar relatórios de registros inválidos.
    pasta_relatorios = Path("dados") / "relatorios"

    exportar_csv(
        relatorio_atas,
        pasta_relatorios / "atas_invalidas.csv",
    )

    exportar_csv(
        relatorio_itens,
        pasta_relatorios / "itens_invalidos.csv",
    )

    exportar_csv(
        relatorio_resultados,
        pasta_relatorios / "resultados_invalidos.csv",
    )

    logging.info("Relatórios de registros inválidos gerados.")
    logging.info("Atas inválidas: %s", len(relatorio_atas))
    logging.info("Itens inválidos: %s", len(relatorio_itens))
    logging.info("Resultados inválidos: %s", len(relatorio_resultados))

    logging.info("Extração concluída.")


if __name__ == "__main__":
    executar()
