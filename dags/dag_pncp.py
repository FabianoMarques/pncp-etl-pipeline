import sys
sys.path.insert(0, "/opt/airflow")

from datetime import datetime
from pathlib import Path
from airflow.sdk import dag, task, get_current_context
from pncp.extracao import extrair_atas
from pncp.exportacao import exportar_json
import json
from pncp.extracao import extrair_dados_complementares
from pncp.transformacao import criar_dataframes
from pncp.validacao import validar_dataframes
from pncp.carga import executar_carga

CAMINHO_DADOS = Path("/opt/airflow/dados")


@dag(
    dag_id="etl_pncp",
    description="Pipeline ETL de atas do PNCP para PostgreSQL",
    schedule=None,
    start_date=datetime(2026, 10, 1),
    catchup=False,
    params={
        "data_inicial": "20261001",
        "data_final": "20261001",
    },
    tags=["PNCP", "ETL"],
)


def dag_pncp():

    @task
    def extrair_atas_task():

        contexto = get_current_context()
        parametros = contexto["params"]

        data_inicial = parametros["data_inicial"]
        data_final = parametros["data_final"]

        print(f"Período da extração: {data_inicial} até {data_final}")

        atas = extrair_atas(
            data_inicial=data_inicial,
            data_final=data_final,
            tamanho_pagina=10,
            max_paginas=1,
        )

        caminho = CAMINHO_DADOS / "atas_extraidas.json"

        exportar_json(atas, caminho)

        print(f"Total de atas extraídas: {len(atas)}")
        print(f"Arquivo gerado: {caminho}")

        return str(caminho)


    @task
    def extrair_complementos(caminho_atas):

        print(f"Lendo atas do arquivo: {caminho_atas}")

        with open(caminho_atas, "r", encoding="utf-8") as arquivo:
            atas = json.load(arquivo)

                
        dados_complementares = extrair_dados_complementares(atas)

        caminho_saida = CAMINHO_DADOS / "dados_pncp_20261001_20261028.json"

        # Preserva os dados extraídos, inclusive os registros com erros.
        exportar_json(dados_complementares, caminho_saida)

        # Identifica atas com falhas nas consultas complementares.
        atas_com_erro = []

        total_erros = 0

        for registro in dados_complementares:

            erros_ata = registro.get("erros") or []

            erros_itens = [
                erro
                for item in registro.get("itens", [])
                for erro in (item.get("erros") or [])
            ]

            erros_registro = erros_ata + erros_itens

            total_erros += len(erros_registro)

            if erros_registro:
                atas_com_erro.append(registro)

        print(f"Total de atas processadas: {len(dados_complementares)}")
        print(f"Atas com falhas: {len(atas_com_erro)}")
        print(f"Total de erros registrados: {total_erros}")
        print(f"Arquivo gerado: {caminho_saida}")

        # Impede o avanço do pipeline quando houver falhas.
        if atas_com_erro:
            raise ValueError(
                f"Extração incompleta: {len(atas_com_erro)} "
                f"ata(s) apresentaram falhas em consultas complementares. "
                f"Consulte o arquivo: {caminho_saida}"
            )

        return str(caminho_saida)




    @task
    def transformar_dados(caminho_json):

        print(f"Lendo arquivo: {caminho_json}")

        with open(caminho_json, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        df_atas, df_itens, df_resultados = criar_dataframes(dados)

        print(f"Atas transformadas: {len(df_atas)}")
        print(f"Itens transformados: {len(df_itens)}")
        print(f"Resultados transformados: {len(df_resultados)}")

        return {
            "total_atas": len(df_atas),
            "total_itens": len(df_itens),
            "total_resultados": len(df_resultados),
        }


    @task
    def validar_dados(caminho_json, resultado_transformacao):

        print(f"Lendo arquivo para validação: {caminho_json}")

        with open(caminho_json, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        df_atas, df_itens, df_resultados = criar_dataframes(dados)

        resultado = validar_dataframes(
            df_atas,
            df_itens,
            df_resultados
        )

        print("Resultado da validação:")
        print(resultado)

        return resultado
    

    @task
    def carregar_postgresql(resultado_validacao):

        if resultado_validacao["status"] != "aprovado":
            raise ValueError(
                "Carga cancelada: os dados não foram aprovados na validação."
            )

        contexto = get_current_context()
        parametros = contexto["params"]

        periodo_inicio = parametros["data_inicial"]
        periodo_fim = parametros["data_final"]

        print(
            f"Iniciando carga no PostgreSQL: "
            f"{periodo_inicio} até {periodo_fim}"
        )

        executar_carga(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim
        )

        print("Carga no PostgreSQL concluída com sucesso!")

        return "Carga concluída"
    


    caminho_atas = extrair_atas_task()
        
    caminho_json = extrair_complementos(caminho_atas)

    resultado_transformacao = transformar_dados(caminho_json)

    resultado_validacao = validar_dados(
        caminho_json,
        resultado_transformacao
    )

    carregar_postgresql(resultado_validacao)



dag_pncp()