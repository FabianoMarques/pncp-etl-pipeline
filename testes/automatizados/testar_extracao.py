import unittest
from unittest.mock import MagicMock, patch

import requests

from pncp.extracao import (
    validar_datas,
    realizar_requisicao,
)


class TestValidarDatas(unittest.TestCase):

    def test_datas_validas(self):
        resultado = validar_datas("20261001", "20261028")
        self.assertIsNone(resultado)

    def test_data_inicial_igual_data_final(self):
        resultado = validar_datas("20261001", "20261001")
        self.assertIsNone(resultado)

    def test_data_inicial_posterior_data_final(self):
        with self.assertRaises(ValueError):
            validar_datas("20261028", "20261001")

    def test_data_inicial_formato_invalido(self):
        with self.assertRaises(ValueError):
            validar_datas("01/10/2026", "20261028")

    def test_data_final_formato_invalido(self):
        with self.assertRaises(ValueError):
            validar_datas("20261001", "2026-10-28")

    def test_data_inexistente(self):
        with self.assertRaises(ValueError):
            validar_datas("20260230", "20260301")


class TestRealizarRequisicao(unittest.TestCase):

    def setUp(self):
        self.sessao = MagicMock()
        self.parametros = {"pagina": 1}

    def test_requisicao_com_sucesso(self):
        resposta = MagicMock()
        resposta.status_code = 200
        resposta.json.return_value = {"data": []}

        self.sessao.get.return_value = resposta

        resultado = realizar_requisicao(
            self.sessao,
            self.parametros,
        )

        self.assertEqual(resultado, {"data": []})
        self.sessao.get.assert_called_once()

    def test_resposta_com_lista_json(self):
        resposta = MagicMock()
        resposta.status_code = 200
        resposta.json.return_value = [{"id": 1}]

        self.sessao.get.return_value = resposta

        resultado = realizar_requisicao(
            self.sessao,
            self.parametros,
        )

        self.assertEqual(resultado, [{"id": 1}])

    def test_resposta_com_json_invalido(self):
        resposta = MagicMock()
        resposta.status_code = 200
        resposta.json.side_effect = requests.exceptions.JSONDecodeError(
            "JSON inválido",
            "conteudo",
            0,
        )

        self.sessao.get.return_value = resposta

        with self.assertRaises(ValueError):
            realizar_requisicao(
                self.sessao,
                self.parametros,
            )

    def test_resposta_com_formato_invalido(self):
        resposta = MagicMock()
        resposta.status_code = 200
        resposta.json.return_value = "resposta inválida"

        self.sessao.get.return_value = resposta

        with self.assertRaises(ValueError):
            realizar_requisicao(
                self.sessao,
                self.parametros,
            )

    def test_erro_http_permanente_sem_retentativa(self):
        resposta = MagicMock()
        resposta.status_code = 400
        resposta.raise_for_status.side_effect = requests.HTTPError(
            response=resposta
        )

        self.sessao.get.return_value = resposta

        with self.assertRaises(requests.HTTPError):
            realizar_requisicao(
                self.sessao,
                self.parametros,
            )

        self.sessao.get.assert_called_once()

    @patch("pncp.extracao.time.sleep")
    def test_retentativa_apos_erro_de_conexao(self, mock_sleep):
        resposta = MagicMock()
        resposta.status_code = 200
        resposta.json.return_value = {"data": []}

        self.sessao.get.side_effect = [
            requests.ConnectionError("Falha de conexão"),
            resposta,
        ]

        resultado = realizar_requisicao(
            self.sessao,
            self.parametros,
        )

        self.assertEqual(resultado, {"data": []})
        self.assertEqual(self.sessao.get.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("pncp.extracao.time.sleep")
    def test_retentativa_apos_erro_http_503(self, mock_sleep):
        resposta_erro = MagicMock()
        resposta_erro.status_code = 503
        resposta_erro.raise_for_status.side_effect = requests.HTTPError(
            response=resposta_erro
        )

        resposta_sucesso = MagicMock()
        resposta_sucesso.status_code = 200
        resposta_sucesso.json.return_value = {"data": []}

        self.sessao.get.side_effect = [
            resposta_erro,
            resposta_sucesso,
        ]

        resultado = realizar_requisicao(
            self.sessao,
            self.parametros,
        )

        self.assertEqual(resultado, {"data": []})
        self.assertEqual(self.sessao.get.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("pncp.extracao.time.sleep")
    def test_retentativa_apos_erro_http_500(self, mock_sleep):
        resposta_erro = MagicMock()
        resposta_erro.status_code = 500
        resposta_erro.raise_for_status.side_effect = requests.HTTPError(
            response=resposta_erro
        )

        resposta_sucesso = MagicMock()
        resposta_sucesso.status_code = 200
        resposta_sucesso.json.return_value = {"data": []}

        self.sessao.get.side_effect = [
            resposta_erro,
            resposta_sucesso,
        ]

        resultado = realizar_requisicao(
            self.sessao,
            self.parametros,
        )

        self.assertEqual(resultado, {"data": []})
        self.assertEqual(self.sessao.get.call_count, 2)
        mock_sleep.assert_called_once()


    @patch("pncp.extracao.time.sleep")
    def test_retentativa_apos_http_429(self, mock_sleep):
        resposta_erro = MagicMock()
        resposta_erro.status_code = 429
        resposta_erro.headers = {"Retry-After": "5"}
        resposta_erro.raise_for_status.side_effect = requests.HTTPError(
            response=resposta_erro
        )

        resposta_sucesso = MagicMock()
        resposta_sucesso.status_code = 200
        resposta_sucesso.json.return_value = {"data": []}

        self.sessao.get.side_effect = [
            resposta_erro,
            resposta_sucesso,
        ]

        resultado = realizar_requisicao(
            self.sessao,
            self.parametros,
        )

        self.assertEqual(resultado, {"data": []})
        self.assertEqual(self.sessao.get.call_count, 2)
        mock_sleep.assert_called_once_with(5)

    @patch("pncp.extracao.time.sleep")
    def test_limite_maximo_de_tentativas(self, mock_sleep):
        self.sessao.get.side_effect = requests.ConnectionError(
            "Falha persistente de conexão"
        )

        with self.assertRaises(requests.ConnectionError):
            realizar_requisicao(
                self.sessao,
                self.parametros,
            )

        self.assertEqual(self.sessao.get.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)


class TestConsultasComplementares(unittest.TestCase):

    @patch("pncp.extracao.realizar_requisicao")
    def test_consultar_detalhes_ata(self, mock_requisicao):
        from pncp.extracao import consultar_detalhes_ata

        mock_requisicao.return_value = {"numeroAta": "123"}

        resultado = consultar_detalhes_ata(
            cnpj="12345678000199",
            ano=2026,
            sequencial_compra=10,
            sequencial_ata=20,
        )

        self.assertEqual(resultado, {"numeroAta": "123"})

        parametros = mock_requisicao.call_args

        self.assertIn(
            "/orgaos/12345678000199/compras/2026/10/atas/20",
            parametros.kwargs["url"],
        )

    @patch("pncp.extracao.realizar_requisicao")
    def test_consultar_itens_contratacao(self, mock_requisicao):
        from pncp.extracao import consultar_itens_contratacao

        mock_requisicao.return_value = [
            {"numeroItem": 1},
            {"numeroItem": 2},
        ]

        resultado = consultar_itens_contratacao(
            cnpj="12345678000199",
            ano=2026,
            sequencial_compra=10,
        )

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]["numeroItem"], 1)

    @patch("pncp.extracao.realizar_requisicao")
    def test_consultar_resultados_item(self, mock_requisicao):
        from pncp.extracao import consultar_resultados_item

        mock_requisicao.return_value = [
            {"numeroItem": 1, "sequencialResultado": 1}
        ]

        resultado = consultar_resultados_item(
            cnpj="12345678000199",
            ano=2026,
            sequencial_compra=10,
            numero_item=1,
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["numeroItem"], 1)

class TestExtrairDadosComplementares(unittest.TestCase):

    def setUp(self):
        self.ata = {
            "cnpjOrgao": "18457226000181",
            "numeroControlePNCPCompra": "18457226000181-1-000015/2023",
            "numeroControlePNCPAta": "18457226000181-1-000015/2023-000001",
            "anoAta": 2023,
        }

    @patch("pncp.extracao.consultar_resultados_item")
    @patch("pncp.extracao.consultar_itens_contratacao")
    @patch("pncp.extracao.consultar_detalhes_ata")
    def test_extracao_complementar_com_sucesso(
        self, mock_detalhes, mock_itens, mock_resultados
    ):
        from pncp.extracao import extrair_dados_complementares

        mock_detalhes.return_value = {"objeto": "Compra de equipamentos"}
        mock_itens.return_value = [
            {"numeroItem": 1, "temResultado": True}
        ]
        mock_resultados.return_value = [
            {"numeroItem": 1, "sequencialResultado": 1}
        ]

        resultado = extrair_dados_complementares([self.ata])

        self.assertEqual(len(resultado), 1)
        self.assertEqual(
            resultado[0]["detalhes"]["objeto"],
            "Compra de equipamentos",
        )
        self.assertEqual(len(resultado[0]["itens"]), 1)
        self.assertEqual(len(resultado[0]["itens"][0]["resultados"]), 1)
        self.assertEqual(resultado[0]["erros"], [])

        mock_detalhes.assert_called_once()
        mock_itens.assert_called_once()
        mock_resultados.assert_called_once()

    @patch("pncp.extracao.consultar_resultados_item")
    @patch("pncp.extracao.consultar_itens_contratacao")
    @patch("pncp.extracao.consultar_detalhes_ata")
    def test_item_sem_resultado_nao_consulta_resultados(
        self, mock_detalhes, mock_itens, mock_resultados
    ):
        from pncp.extracao import extrair_dados_complementares

        mock_detalhes.return_value = {"objeto": "Teste"}
        mock_itens.return_value = [
            {"numeroItem": 1, "temResultado": False}
        ]

        resultado = extrair_dados_complementares([self.ata])

        self.assertEqual(
            resultado[0]["itens"][0]["resultados"],
            [],
        )
        mock_resultados.assert_not_called()

    @patch("pncp.extracao.consultar_itens_contratacao")
    @patch("pncp.extracao.consultar_detalhes_ata")
    def test_falha_na_consulta_detalhes(
        self, mock_detalhes, mock_itens
    ):
        import requests
        from pncp.extracao import extrair_dados_complementares

        mock_detalhes.side_effect = requests.exceptions.Timeout(
            "Tempo limite excedido"
        )
        mock_itens.return_value = []

        resultado = extrair_dados_complementares([self.ata])

        self.assertIsNone(resultado[0]["detalhes"])
        self.assertEqual(resultado[0]["itens"], [])
        self.assertEqual(len(resultado[0]["erros"]), 1)
        self.assertEqual(
            resultado[0]["erros"][0]["etapa"],
            "detalhes",
        )

    @patch("pncp.extracao.consultar_resultados_item")
    @patch("pncp.extracao.consultar_itens_contratacao")
    @patch("pncp.extracao.consultar_detalhes_ata")
    def test_falha_na_consulta_resultados(
        self, mock_detalhes, mock_itens, mock_resultados
    ):
        import requests
        from pncp.extracao import extrair_dados_complementares

        mock_detalhes.return_value = {"objeto": "Teste"}
        mock_itens.return_value = [
            {"numeroItem": 1, "temResultado": True}
        ]
        mock_resultados.side_effect = requests.exceptions.HTTPError(
            "Erro HTTP 503"
        )

        resultado = extrair_dados_complementares([self.ata])

        item = resultado[0]["itens"][0]

        self.assertEqual(item["resultados"], [])
        self.assertEqual(len(item["erros"]), 1)
        self.assertEqual(item["erros"][0]["etapa"], "resultados")
        self.assertEqual(resultado[0]["erros"], [])

    @patch("pncp.extracao.consultar_itens_contratacao")
    @patch("pncp.extracao.consultar_detalhes_ata")
    def test_falha_na_consulta_itens(
        self, mock_detalhes, mock_itens
    ):
        import requests
        from pncp.extracao import extrair_dados_complementares

        mock_detalhes.return_value = {"objeto": "Teste"}
        mock_itens.side_effect = requests.exceptions.HTTPError(
            "Erro HTTP 503"
        )

        resultado = extrair_dados_complementares([self.ata])

        self.assertEqual(resultado[0]["itens"], [])
        self.assertEqual(len(resultado[0]["erros"]), 1)
        self.assertEqual(
            resultado[0]["erros"][0]["etapa"],
            "itens",
        )

    def test_rejeita_entrada_que_nao_seja_lista(self):
        from pncp.extracao import extrair_dados_complementares

        with self.assertRaises(ValueError):
            extrair_dados_complementares(None)

    def test_rejeita_ata_com_formato_invalido(self):
        from pncp.extracao import extrair_dados_complementares

        with self.assertRaises(ValueError):
            extrair_dados_complementares(["ata inválida"])

    def test_rejeita_identificadores_incompletos(self):
        from pncp.extracao import extrair_dados_complementares

        ata_incompleta = {
            "cnpjOrgao": "18457226000181",
            "anoAta": 2023,
        }

        with self.assertRaises(ValueError):
            extrair_dados_complementares([ata_incompleta])


class TestExtrairAtas(unittest.TestCase):

    @patch("pncp.extracao.realizar_requisicao")
    def test_extracao_com_sucesso(self, mock_requisicao):
        from pncp.extracao import extrair_atas

        mock_requisicao.return_value = {
            "data": [
                {"numeroControlePNCPAta": "ATA001"},
                {"numeroControlePNCPAta": "ATA002"},
            ],
            "totalPaginas": 1,
        }

        resultado = extrair_atas(
            data_inicial="20261001",
            data_final="20261028",
        )

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]["numeroControlePNCPAta"], "ATA001")
        self.assertEqual(resultado[1]["numeroControlePNCPAta"], "ATA002")

        parametros = mock_requisicao.call_args.args[1]

        self.assertEqual(parametros["dataInicial"], "20261001")
        self.assertEqual(parametros["dataFinal"], "20261028")
        self.assertEqual(parametros["pagina"], 1)
        self.assertEqual(parametros["tamanhoPagina"], 10)

    @patch("pncp.extracao.realizar_requisicao")
    def test_extracao_com_resposta_vazia(self, mock_requisicao):
        from pncp.extracao import extrair_atas

        mock_requisicao.return_value = {
            "data": [],
            "totalPaginas": 0,
        }

        resultado = extrair_atas(
            data_inicial="20261001",
            data_final="20261028",
        )

        self.assertEqual(resultado, [])
        mock_requisicao.assert_called_once()

    @patch("pncp.extracao.realizar_requisicao")
    def test_rejeita_campo_data_invalido(self, mock_requisicao):
        from pncp.extracao import extrair_atas

        mock_requisicao.return_value = {
            "data": None,
            "totalPaginas": 1,
        }

        with self.assertRaises(ValueError):
            extrair_atas(
                data_inicial="20261001",
                data_final="20261028",
            )

    @patch("pncp.extracao.realizar_requisicao")
    def test_rejeita_registros_com_formato_invalido(
        self, mock_requisicao
    ):
        from pncp.extracao import extrair_atas

        mock_requisicao.return_value = {
            "data": [
                {"numeroControlePNCPAta": "ATA001"},
                "registro inválido",
            ],
            "totalPaginas": 1,
        }

        with self.assertRaises(ValueError):
            extrair_atas(
                data_inicial="20261001",
                data_final="20261028",
            )

    @patch("pncp.extracao.realizar_requisicao")
    def test_rejeita_total_paginas_invalido(self, mock_requisicao):
        from pncp.extracao import extrair_atas

        mock_requisicao.return_value = {
            "data": [],
            "totalPaginas": "inválido",
        }

        with self.assertRaises(ValueError):
            extrair_atas(
                data_inicial="20261001",
                data_final="20261028",
            )

    @patch("pncp.extracao.realizar_requisicao")
    def test_rejeita_tamanho_pagina_zero(self, mock_requisicao):
        from pncp.extracao import extrair_atas

        with self.assertRaises(ValueError):
            extrair_atas(
                data_inicial="20261001",
                data_final="20261028",
                tamanho_pagina=0,
            )

        mock_requisicao.assert_not_called()

class TestPaginacao(unittest.TestCase):

    @patch("pncp.extracao.time.sleep")
    @patch("pncp.extracao.realizar_requisicao")
    def test_extrair_atas_com_multiplas_paginas(
        self, mock_requisicao, mock_sleep
    ):
        from pncp.extracao import extrair_atas

        mock_requisicao.side_effect = [
            {
                "data": [
                    {"numeroControlePNCPAta": "ATA001"},
                    {"numeroControlePNCPAta": "ATA002"},
                ],
                "totalPaginas": 2,
            },
            {
                "data": [
                    {"numeroControlePNCPAta": "ATA003"},
                ],
                "totalPaginas": 2,
            },
        ]

        resultado = extrair_atas(
            data_inicial="20261001",
            data_final="20261028",
            tamanho_pagina=2,
        )

        self.assertEqual(len(resultado), 3)
        self.assertEqual(mock_requisicao.call_count, 2)
        self.assertEqual(
            [item["numeroControlePNCPAta"] for item in resultado],
            ["ATA001", "ATA002", "ATA003"],
        )

        primeira_chamada = mock_requisicao.call_args_list[0]
        segunda_chamada = mock_requisicao.call_args_list[1]

        self.assertEqual(primeira_chamada.args[1]["pagina"], 1)
        self.assertEqual(segunda_chamada.args[1]["pagina"], 2)
        mock_sleep.assert_called_once()

    @patch("pncp.extracao.time.sleep")
    @patch("pncp.extracao.realizar_requisicao")
    def test_extrair_atas_respeita_limite_de_paginas(
        self, mock_requisicao, mock_sleep
    ):
        from pncp.extracao import extrair_atas

        mock_requisicao.return_value = {
            "data": [
                {"numeroControlePNCPAta": "ATA001"},
                {"numeroControlePNCPAta": "ATA002"},
            ],
            "totalPaginas": 5,
        }

        resultado = extrair_atas(
            data_inicial="20261001",
            data_final="20261028",
            tamanho_pagina=2,
            max_paginas=1,
        )

        self.assertEqual(len(resultado), 2)
        mock_requisicao.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("pncp.extracao.time.sleep")
    @patch("pncp.extracao.realizar_requisicao")
    def test_extrair_atas_sem_total_paginas(
        self, mock_requisicao, mock_sleep
    ):
        from pncp.extracao import extrair_atas

        mock_requisicao.side_effect = [
            {
                "data": [
                    {"numeroControlePNCPAta": "ATA001"},
                    {"numeroControlePNCPAta": "ATA002"},
                ]
            },
            {
                "data": [
                    {"numeroControlePNCPAta": "ATA003"}
                ]
            },
        ]

        resultado = extrair_atas(
            data_inicial="20261001",
            data_final="20261028",
            tamanho_pagina=2,
        )

        self.assertEqual(len(resultado), 3)
        self.assertEqual(mock_requisicao.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)

    @patch("pncp.extracao.time.sleep")
    @patch("pncp.extracao.realizar_requisicao")
    def test_consultar_itens_com_multiplas_paginas(
        self, mock_requisicao, mock_sleep
    ):
        from pncp.extracao import consultar_itens_contratacao

        mock_requisicao.side_effect = [
            [
                {"numeroItem": 1},
                {"numeroItem": 2},
            ],
            [
                {"numeroItem": 3},
            ],
        ]

        resultado = consultar_itens_contratacao(
            cnpj="18457226000181",
            ano=2023,
            sequencial_compra=15,
            tamanho_pagina=2,
        )

        self.assertEqual(len(resultado), 3)
        self.assertEqual(mock_requisicao.call_count, 2)

        primeira_chamada = mock_requisicao.call_args_list[0]
        segunda_chamada = mock_requisicao.call_args_list[1]

        self.assertEqual(primeira_chamada.args[1]["pagina"], 1)
        self.assertEqual(segunda_chamada.args[1]["pagina"], 2)

        self.assertEqual(
            [item["numeroItem"] for item in resultado],
            [1, 2, 3],
        )

        self.assertEqual(mock_sleep.call_count, 1)

    @patch("pncp.extracao.time.sleep")
    @patch("pncp.extracao.realizar_requisicao")
    def test_consultar_itens_com_resposta_vazia(
        self, mock_requisicao, mock_sleep
    ):
        from pncp.extracao import consultar_itens_contratacao

        mock_requisicao.return_value = []

        resultado = consultar_itens_contratacao(
            cnpj="18457226000181",
            ano=2023,
            sequencial_compra=15,
            tamanho_pagina=2,
        )

        self.assertEqual(resultado, [])
        mock_requisicao.assert_called_once()
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()