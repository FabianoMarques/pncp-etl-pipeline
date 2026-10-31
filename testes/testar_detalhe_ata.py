import requests
from pprint import pprint

URL = (
    "https://pncp.gov.br/api/pncp/v1/"
    "orgaos/18457226000181/compras/2023/15/atas/1"
)

try:
    resposta = requests.get(URL, timeout=30)

    print("Status HTTP:", resposta.status_code)
    resposta.raise_for_status()

    dados = resposta.json()

    print("\nDados retornados pela consulta:")
    pprint(dados, sort_dicts=False)

    if isinstance(dados, dict):
        print("\nCampos disponíveis:")
        for campo in dados:
            print("-", campo)

except requests.RequestException as erro:
    print("Erro na consulta ao PNCP:", erro)

except ValueError as erro:
    print("Erro ao interpretar a resposta JSON:", erro)

