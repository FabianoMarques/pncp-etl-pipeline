from pncp.extracao import extrair_atas

atas = extrair_atas(
    data_inicial="20261001",
    data_final="20261028",
    tamanho_pagina=10,
    max_paginas=1,
)

ata = atas[9]

print("\nIDENTIFICADORES DA 10ª ATA")
print("Controle da compra:", ata.get("numeroControlePNCPCompra"))
print("Controle da ata:", ata.get("numeroControlePNCPAta"))
print("Ano da ata:", ata.get("anoAta"))
print("CNPJ do órgão:", ata.get("cnpjOrgao"))