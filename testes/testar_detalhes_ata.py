from pprint import pprint

from pncp.extracao import consultar_detalhes_ata


dados = consultar_detalhes_ata(
    cnpj="18457226000181",
    ano=2023,
    sequencial_compra=15,
    sequencial_ata=1,
)

pprint(dados)