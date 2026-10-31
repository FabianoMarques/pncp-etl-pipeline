import logging
from pprint import pprint

from pncp.extracao import extrair_atas
from pncp.validacao import validar_registros

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

if __name__ == "__main__":
    print("\nETAPA 1 — EXTRAÇÃO")

    registros = extrair_atas(
        data_inicial="20261001",
        data_final="20261028",
        tamanho_pagina=10,
        max_paginas=2,
    )

    print(f"\nRegistros extraídos: {len(registros)}")

    if registros:
        print("\nETAPA 1.1 — CAMPOS E VALORES DO PRIMEIRO REGISTRO")

        print(f"Quantidade de campos: {len(registros[0])}")

        print("\nCampos disponíveis:")
        for campo in registros[0].keys():
            print(f"- {campo}")

        print("\nDados completos do primeiro registro:")
        pprint(registros[0], sort_dicts=False)

    print("\nETAPA 2 — VALIDAÇÃO")

    registros_validos = validar_registros(registros)

    print(f"Registros aprovados: {len(registros_validos)}")

    print("\nETL PARCIAL CONCLUÍDO COM SUCESSO!")
