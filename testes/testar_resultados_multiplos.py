import requests

URL_BASE = (
    "https://pncp.gov.br/api/pncp/v1/"
    "orgaos/18457226000181/"
    "compras/2023/15/itens"
)


def consultar_resultados(numero_item):
    url = (
        f"{URL_BASE}/{numero_item}/resultados"
    )

    resposta = requests.get(
        url,
        timeout=30
    )

    print(f"\nItem consultado: {numero_item}")
    print("Status HTTP:", resposta.status_code)

    resposta.raise_for_status()

    dados = resposta.json()

    if not isinstance(dados, list):
        raise ValueError(
            "A resposta não é uma lista."
        )

    print("Quantidade de resultados:", len(dados))

    for resultado in dados:
        print(
            "  Sequencial:",
            resultado.get("sequencialResultado")
        )
        print(
            "  Fornecedor:",
            resultado.get("nomeRazaoSocialFornecedor")
        )
        print(
            "  Valor homologado:",
            resultado.get("valorTotalHomologado")
        )


try:
    consultar_resultados(1)
    consultar_resultados(2)

except requests.exceptions.RequestException as erro:
    print("Erro na requisição:", erro)

except ValueError as erro:
    print("Erro nos dados retornados:", erro)