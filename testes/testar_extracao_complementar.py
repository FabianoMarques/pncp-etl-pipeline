from pncp.extracao import (
    extrair_atas,
    extrair_dados_complementares,
)

# Extrai uma pequena quantidade de atas para o teste.
atas = extrair_atas(
    data_inicial="20261001",
    data_final="20261028",
    tamanho_pagina=10,
    max_paginas=1,
)

# Testa a extração complementar com apenas uma ata.
resultado = extrair_dados_complementares(
    atas=atas[:1],
    tamanho_pagina_itens=2,
)

print("\nExtração complementar concluída.")

print(f"Atas processadas: {len(resultado)}")

if resultado:
    ata = resultado[0]

    print(f"Itens encontrados: {len(ata['itens'])}")

    for registro in ata["itens"]:
        item = registro["item"]
        resultados = registro["resultados"]

        print(
            f"Item {item.get('numeroItem')} | "
            f"Resultados: {len(resultados)}"
        )