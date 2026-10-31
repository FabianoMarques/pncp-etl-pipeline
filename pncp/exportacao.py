import json
from pathlib import Path


def exportar_json(dados, caminho_arquivo):
    """
    Exporta os dados extraídos para um arquivo JSON.
    """

    caminho = Path(caminho_arquivo)

    # Cria o diretório caso ainda não exista.
    caminho.parent.mkdir(parents=True, exist_ok=True)

    # Grava os dados no arquivo JSON.
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4,
        )

    return caminho

def exportar_csv(dataframe, caminho_arquivo):
    """
    Exporta um DataFrame para um arquivo CSV.
    """

    caminho = Path(caminho_arquivo)

    # Cria o diretório caso ainda não exista.
    caminho.parent.mkdir(parents=True, exist_ok=True)

    # Grava os dados no arquivo CSV.
    dataframe.to_csv(
        caminho,
        index=False,
        encoding="utf-8-sig",
        sep=";",
    )

    return caminho