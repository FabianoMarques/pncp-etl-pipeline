import json
from pathlib import Path
import pandas as pd
import re


def ler_json():
    """
    Lê o arquivo JSON original da extração do PNCP.
    """

    caminho_arquivo = (
        Path(__file__).resolve().parent.parent
        / "dados"
        / "dados_pncp_20261001_20261028.json"
    )

    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    return dados


def inspecionar_dados(dados):
    """
    Apresenta informações sobre a estrutura dos dados extraídos.
    """

    print(f"Total de registros: {len(dados)}")

    if not dados:
        print("O arquivo não possui registros.")
        return

    primeiro_registro = dados[0]

    print("\nEstrutura do registro:")
    print(list(primeiro_registro.keys()))

    for chave, valor in primeiro_registro.items():

        print(f"\nBloco: {chave}")
        print(f"Tipo: {type(valor).__name__}")

        if isinstance(valor, dict):
            print(f"Campos: {list(valor.keys())}")

        elif isinstance(valor, list):
            print(f"Quantidade de elementos: {len(valor)}")

            if valor and isinstance(valor[0], dict):
                print(f"Campos do primeiro elemento: {list(valor[0].keys())}")


def mostrar_campos(titulo, dados):
    """
    Exibe os campos e os tipos de dados de um dicionário.
    """

    print(f"\n--- {titulo} ---")

    if not isinstance(dados, dict):
        print(f"Tipo encontrado: {type(dados).__name__}")
        return

    for campo, valor in dados.items():
        print(f"{campo}: {type(valor).__name__}")


def inspecionar_dados(dados):

    print(f"Total de atas: {len(dados)}")

    total_itens = 0
    total_resultados = 0

    for registro in dados:
        itens = registro.get("itens", [])

        total_itens += len(itens)

        for elemento in itens:
            total_resultados += len(elemento.get("resultados", []))

    print(f"Total de itens: {total_itens}")
    print(f"Total de resultados: {total_resultados}")

    if not dados:
        print("Arquivo sem registros.")
        return

    primeiro_registro = dados[0]

    # Informações principais da ata
    mostrar_campos("ATA", primeiro_registro.get("ata", {}))

    # Informações complementares
    detalhes = primeiro_registro.get("detalhes", {})

    mostrar_campos("DETALHES", detalhes)

    # Estruturas aninhadas de detalhes
    mostrar_campos(
        "DETALHES - ORGAO ENTIDADE",
        detalhes.get("orgaoEntidade", {})
    )

    mostrar_campos(
        "DETALHES - UNIDADE ORGAO",
        detalhes.get("unidadeOrgao", {})
    )

    # Primeiro item
    itens = primeiro_registro.get("itens", [])

    if itens:

        primeiro_item = itens[0]

        mostrar_campos(
            "ITEM",
            primeiro_item.get("item", {})
        )

        # Primeiro resultado
        resultados = primeiro_item.get("resultados", [])

        if resultados:
            mostrar_campos(
                "RESULTADO",
                resultados[0]
            )
        else:
            print("\nO primeiro item não possui resultados.")


def inspecionar_relacionamentos(dados):

    from collections import Counter

    ids_atas = []
    itens_por_ata = Counter()
    resultados_por_item = Counter()

    itens_sem_numero = 0
    resultados_sem_numero = 0
    resultados_sem_sequencial = 0
    resultados_sem_item_correspondente = 0

    for registro in dados:

        ata = registro.get("ata", {})
        id_ata = ata.get("numeroControlePNCPAta")

        ids_atas.append(id_ata)

        numeros_itens = set()

        for elemento in registro.get("itens", []):

            item = elemento.get("item", {})
            numero_item = item.get("numeroItem")

            if numero_item is None:
                itens_sem_numero += 1
                continue

            numeros_itens.add(numero_item)
            itens_por_ata[id_ata] += 1

        for elemento in registro.get("itens", []):

            item = elemento.get("item", {})
            numero_item = item.get("numeroItem")

            for resultado in elemento.get("resultados", []):

                numero_item_resultado = resultado.get("numeroItem")
                sequencial = resultado.get("sequencialResultado")

                if numero_item_resultado is None:
                    resultados_sem_numero += 1

                if sequencial is None:
                    resultados_sem_sequencial += 1

                if numero_item_resultado not in numeros_itens:
                    resultados_sem_item_correspondente += 1

                resultados_por_item[
                    (id_ata, numero_item)
                ] += 1

    print("\n--- IDENTIFICADORES DAS ATAS ---")
    print(f"Total de atas: {len(ids_atas)}")
    print(f"Atas sem identificador: {ids_atas.count(None)}")
    print(f"Identificadores duplicados: {len(ids_atas) - len(set(ids_atas))}")

    print("\n--- ITENS ---")
    print(f"Total de itens: {sum(itens_por_ata.values())}")
    print(f"Itens sem número: {itens_sem_numero}")

    print("\n--- RESULTADOS ---")
    print(f"Total de resultados: {sum(resultados_por_item.values())}")
    print(f"Resultados sem número do item: {resultados_sem_numero}")
    print(f"Resultados sem sequencial: {resultados_sem_sequencial}")
    print(f"Resultados sem item correspondente: {resultados_sem_item_correspondente}")

    print("\n--- QUANTIDADE DE ITENS POR ATA ---")

    for id_ata, quantidade in itens_por_ata.items():
        print(f"{id_ata}: {quantidade} itens")

    print("\n--- RESULTADOS POR ITEM ---")

    for identificacao, quantidade in resultados_por_item.items():
        print(f"Ata/Item {identificacao}: {quantidade} resultados")


def criar_dataframes(dados):

    registros_atas = []
    registros_itens = []
    registros_resultados = []

    for indice, registro in enumerate(dados):

        ata = registro.get("ata", {})
        detalhes = registro.get("detalhes", {})
        itens = registro.get("itens", [])

        id_ata = ata.get("numeroControlePNCPAta")

        # DataFrame de atas
        registro_ata = ata.copy()

        registro_ata["id_origem"] = indice

        # Informações complementares selecionadas
        orgao = detalhes.get("orgaoEntidade") or {}
        unidade = detalhes.get("unidadeOrgao") or {}

        registro_ata["razaoSocialOrgao"] = orgao.get("razaoSocial")
        registro_ata["esferaOrgao"] = orgao.get("esferaId")
        registro_ata["poderOrgao"] = orgao.get("poderId")

        registro_ata["municipioUnidade"] = unidade.get("municipioNome")
        registro_ata["ufUnidade"] = unidade.get("ufSigla")
        registro_ata["codigoIbgeUnidade"] = unidade.get("codigoIbge")

        registros_atas.append(registro_ata)

        # DataFrames de itens e resultados
        for registro_item in itens:

            item = registro_item.get("item", {})
            resultados = registro_item.get("resultados", [])

            registro_item_df = item.copy()

            registro_item_df["id_origem"] = indice
            registro_item_df["numeroControlePNCPAta"] = id_ata

            registros_itens.append(registro_item_df)

            for resultado in resultados:

                registro_resultado = resultado.copy()

                registro_resultado["id_origem"] = indice
                registro_resultado["numeroControlePNCPAta"] = id_ata
                registro_resultado["numeroItemOrigem"] = item.get("numeroItem")

                registros_resultados.append(registro_resultado)

    df_atas = pd.DataFrame(registros_atas)
    df_itens = pd.DataFrame(registros_itens)
    df_resultados = pd.DataFrame(registros_resultados)

    return df_atas, df_itens, df_resultados


def normalizar_colunas(df):

    novas_colunas = []

    for coluna in df.columns:

        nome = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', coluna)
        nome = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', nome)

        nome = nome.lower()

        novas_colunas.append(nome)

    df.columns = novas_colunas

    return df

def converter_datas(df, colunas_data):

    for coluna in colunas_data:

        if coluna in df.columns:

            df[coluna] = pd.to_datetime(
                df[coluna],
                format="ISO8601",
                errors="coerce"
            )

    return df




if __name__ == "__main__":

    dados = ler_json()

    inspecionar_dados(dados)