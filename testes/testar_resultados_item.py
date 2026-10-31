import requests
import json

URL = (
"https://pncp.gov.br/api/pncp/v1/"
"orgaos/18457226000181/"
"compras/2023/15/itens/1/resultados"
)

try:
    resposta = requests.get(URL, timeout=30)


    print("Status HTTP:", resposta.status_code)
    resposta.raise_for_status()

    dados = resposta.json()

    print("\nEstrutura da resposta:")
    print(json.dumps(dados, indent=4, ensure_ascii=False))


except requests.exceptions.Timeout:
    print("Erro: a requisição excedeu o tempo limite.")

except requests.exceptions.RequestException as erro:
    print("Erro na requisição:", erro)

except ValueError:
    print("Erro: a resposta não contém JSON válido.")
