import logging

from pncp.extracao import extrair_atas


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


if __name__ == "__main__":
    registros = extrair_atas(
        data_inicial="20261001",
        data_final="20261028",
        tamanho_pagina=10,
        max_paginas=2,
    )

    print("\nTotal de registros extraídos:", len(registros))

    if registros:
        print("\nCampos do primeiro registro:")
        print(list(registros[0].keys()))

        print("\nPrimeiro registro:")
        print(registros[0])
    else:
        print("A consulta não retornou registros.")

