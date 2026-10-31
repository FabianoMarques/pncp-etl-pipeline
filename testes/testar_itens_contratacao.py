from pncp.extracao import consultar_itens_contratacao

itens = consultar_itens_contratacao(
    cnpj="18457226000181",
    ano=2023,
    sequencial_compra=15,
    tamanho_pagina=2,
)

print(f"\nTotal de itens extraídos: {len(itens)}")

for item in itens:
    print(
        f"Item: {item.get('numeroItem')} | "
        f"Descrição: {item.get('descricao')}"
    )