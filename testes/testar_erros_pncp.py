"""
Testes automatizados para verificar o tratamento de erros
na extração de atas do PNCP.
"""
from pncp.extracao import (
    extrair_atas,
    extrair_dados_complementares,
    realizar_requisicao,
)

import unittest
from unittest.mock import MagicMock, patch

import requests

#from pncp.extracao import realizar_requisicao

from pncp.extracao import extrair_atas, extrair_dados_complementares, realizar_requisicao



class TestarErrosPNCP(unittest.TestCase):
    """Testa o comportamento da extração diante de falhas."""

    def setUp(self):
        """Prepara os dados utilizados nos testes."""
        self.sessao = requests.Session()
        self.parametros = {"pagina": 1}

    def tearDown(self):
        """Encerra a sessão HTTP após cada teste."""
        self.sessao.close()

    def criar_resposta(self, status_code=200, dados=None):
        """
        Cria uma resposta HTTP simulada para os testes.

        Args:
            status_code: Código HTTP da resposta.
            dados: Conteúdo JSON retornado pela API.

        Returns:
            Resposta HTTP simulada.
        """
        resposta = MagicMock()
        resposta.status_code = status_code
        resposta.headers = {}
        resposta.json.return_value = (
            dados if dados is not None else {"data": []}
        )

        return resposta

    def criar_erro_http(self, resposta, mensagem):
        """
        Configura uma resposta para gerar um erro HTTP.

        Args:
            resposta: Resposta HTTP simulada.
            mensagem: Mensagem associada ao erro.

        Returns:
            Exceção HTTP configurada.
        """
        erro = requests.HTTPError(mensagem)
        erro.response = resposta

        resposta.raise_for_status.side_effect = erro

        return erro

    def test_timeout(self):
        """Verifica as retentativas quando ocorre timeout."""

        resposta_ok = self.criar_resposta()

        with (
            patch.object(self.sessao, "get") as mock_get,
            patch("pncp.extracao.time.sleep") as mock_sleep,
        ):
            mock_get.side_effect = [
                requests.Timeout("Tempo limite excedido"),
                resposta_ok,
            ]

            resultado = realizar_requisicao(
                self.sessao,
                self.parametros,
            )

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(resultado, {"data": []})

        mock_sleep.assert_called_once_with(2)

    def test_http_500_apos_tres_tentativas(self):
        """Verifica se HTTP 500 respeita o limite de tentativas."""

        resposta = self.criar_resposta(status_code=500)

        self.criar_erro_http(
            resposta,
            "Erro HTTP 500",
        )

        with (
            patch.object(self.sessao, "get") as mock_get,
            patch("pncp.extracao.time.sleep") as mock_sleep,
        ):
            mock_get.return_value = resposta

            with self.assertRaises(requests.HTTPError):
                realizar_requisicao(
                    self.sessao,
                    self.parametros,
                )

        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_http_429(self):
        """Verifica se HTTP 429 provoca nova tentativa."""

        resposta_429 = self.criar_resposta(status_code=429)
        resposta_429.headers = {"Retry-After": "3"}

        self.criar_erro_http(
            resposta_429,
            "Limite de requisições excedido",
        )

        resposta_ok = self.criar_resposta()

        with (
            patch.object(self.sessao, "get") as mock_get,
            patch("pncp.extracao.time.sleep") as mock_sleep,
        ):
            mock_get.side_effect = [
                resposta_429,
                resposta_ok,
            ]

            resultado = realizar_requisicao(
                self.sessao,
                self.parametros,
            )

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(resultado, {"data": []})

        mock_sleep.assert_called_once_with(3)

    def test_json_invalido(self):
        """Verifica se uma resposta JSON inválida gera erro."""

        resposta = self.criar_resposta()

        resposta.json.side_effect = requests.exceptions.JSONDecodeError(
            "JSON inválido",
            "<html>",
            0,
        )

        with (
            patch.object(self.sessao, "get") as mock_get,
            patch("pncp.extracao.time.sleep") as mock_sleep,
        ):
            mock_get.return_value = resposta

            with self.assertRaises(ValueError):
                realizar_requisicao(
                    self.sessao,
                    self.parametros,
                )

        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()



    def test_json_com_estrutura_incorreta(self):
        """Verifica se um JSON que não contém um objeto gera erro."""

        resposta = self.criar_resposta()

        resposta.json.return_value = "conteúdo inválido"

        with (
            patch.object(self.sessao, "get") as mock_get,
            patch("pncp.extracao.time.sleep") as mock_sleep,
        ):
            mock_get.return_value = resposta

            with self.assertRaises(ValueError):
                realizar_requisicao(
                    self.sessao,
                    self.parametros,
                )

        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()


    def test_campo_data_invalido(self):
        """Verifica se o campo data precisa conter uma lista."""

        resposta = self.criar_resposta(
            dados={"data": "conteúdo inválido"}
        )

        with (
            patch.object(self.sessao, "get") as mock_get,
            patch("pncp.extracao.time.sleep") as mock_sleep,
        ):
            mock_get.return_value = resposta

            resultado = realizar_requisicao(
                self.sessao,
                self.parametros,
            )

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(
            resultado,
            {"data": "conteúdo inválido"},
        )
        mock_sleep.assert_not_called()



    def test_extracao_com_campo_data_invalido(self):
        """Verifica se a extração rejeita um campo data que não é lista."""

        resposta = {"data": "conteúdo inválido"}

        with patch(
            "pncp.extracao.realizar_requisicao",
            return_value=resposta,
        ):
            with self.assertRaises(ValueError):
                extrair_atas(
                    data_inicial="20261001",
                    data_final="20261028",
                    tamanho_pagina=10,
                    max_paginas=1,
                )


    def test_total_paginas_invalido(self):
        """Verifica se a extração rejeita totalPaginas inválido."""

        resposta = {
            "data": [{"id": 1}],
            "totalPaginas": "valor_invalido",
        }

        with patch(
            "pncp.extracao.realizar_requisicao",
            return_value=resposta,
        ):
            with self.assertRaises(ValueError):
                extrair_atas(
                    data_inicial="20261001",
                    data_final="20261028",
                    tamanho_pagina=10,
                    max_paginas=1,
                )


    def test_http_400_sem_retentativa(self):
        """Verifica se HTTP 400 interrompe sem novas tentativas."""

        resposta = self.criar_resposta(status_code=400)

        self.criar_erro_http(
            resposta,
            "Requisição inválida",
        )

        with (
            patch.object(self.sessao, "get") as mock_get,
            patch("pncp.extracao.time.sleep") as mock_sleep,
        ):
            mock_get.return_value = resposta

            with self.assertRaises(requests.HTTPError):
                realizar_requisicao(
                    self.sessao,
                    self.parametros,
                )

        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()

    def test_http_404_sem_retentativa(self):
        """Verifica se HTTP 404 interrompe sem novas tentativas."""

        resposta = self.criar_resposta(status_code=404)

        self.criar_erro_http(
            resposta,
            "Recurso não encontrado",
        )

        with (
            patch.object(self.sessao, "get") as mock_get,
            patch("pncp.extracao.time.sleep") as mock_sleep,
        ):
            mock_get.return_value = resposta

            with self.assertRaises(requests.HTTPError):
                realizar_requisicao(
                    self.sessao,
                    self.parametros,
                )

        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()

    def test_falha_consulta_detalhes_ata(self):
        """Verifica se a falha nos detalhes é registrada."""

        ata = {
            "cnpjOrgao": "18457226000181",
            "numeroControlePNCPCompra": "18457226000181-1-000015/2023",
            "numeroControlePNCPAta": "18457226000181-1-000015/2023-000001",
            "anoAta": 2023,
        }

        with (
            patch(
                "pncp.extracao.consultar_detalhes_ata",
                side_effect=requests.HTTPError("Erro HTTP 500"),
            ),
            patch(
                "pncp.extracao.consultar_itens_contratacao",
                return_value=[],
            ) as mock_itens,
        ):
            resultado = extrair_dados_complementares([ata])

        self.assertEqual(len(resultado), 1)
        self.assertEqual(len(resultado[0]["erros"]), 1)
        self.assertEqual(resultado[0]["erros"][0]["etapa"], "detalhes")

        mock_itens.assert_called_once()


    def test_falha_consulta_itens(self):
        """Verifica se a falha na consulta dos itens é registrada."""

        ata = {
            "cnpjOrgao": "18457226000181",
            "numeroControlePNCPCompra": "18457226000181-1-000015/2023",
            "numeroControlePNCPAta": "18457226000181-1-000015/2023-000001",
            "anoAta": 2023,
        }

        with (
            patch(
                "pncp.extracao.consultar_detalhes_ata",
                return_value={"numeroAtaRegistroPreco": "NPERP 003/2023"},
            ),
            patch(
                "pncp.extracao.consultar_itens_contratacao",
                side_effect=requests.HTTPError("Erro HTTP 500"),
            ),
        ):
            resultado = extrair_dados_complementares([ata])

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["itens"], [])
        self.assertEqual(len(resultado[0]["erros"]), 1)
        self.assertEqual(resultado[0]["erros"][0]["etapa"], "itens")



    def test_falha_consulta_resultados_item(self):
        """Verifica se a falha nos resultados de um item não interrompe os demais."""

        ata = {
            "cnpjOrgao": "18457226000181",
            "numeroControlePNCPCompra": "18457226000181-1-000015/2023",
            "numeroControlePNCPAta": "18457226000181-1-000015/2023-000001",
            "anoAta": 2023,
        }

        itens = [
            {"numeroItem": 1, "temResultado": True},
            {"numeroItem": 2, "temResultado": True},
        ]

        with (
            patch(
                "pncp.extracao.consultar_detalhes_ata",
                return_value={"numeroAtaRegistroPreco": "NPERP 003/2023"},
            ),
            patch(
                "pncp.extracao.consultar_itens_contratacao",
                return_value=itens,
            ),
            patch(
                "pncp.extracao.consultar_resultados_item",
                side_effect=[
                    requests.HTTPError("Erro HTTP 500"),
                    [{"nomeRazaoSocialFornecedor": "Fornecedor teste"}],
                ],
            ) as mock_resultados,
        ):
            resultado = extrair_dados_complementares([ata])

        itens_resultado = resultado[0]["itens"]

        self.assertEqual(len(itens_resultado), 2)
        self.assertEqual(itens_resultado[0]["resultados"], [])
        self.assertEqual(
            itens_resultado[0]["erros"][0]["etapa"],
            "resultados",
        )
        self.assertEqual(len(itens_resultado[1]["resultados"]), 1)

        mock_resultados.assert_called()



    def test_falha_em_uma_ata_nao_interrompe_as_demais(self):
        """Verifica se a falha em uma ata não interrompe as seguintes."""

        ata1 = {
            "cnpjOrgao": "18457226000181",
            "numeroControlePNCPCompra": "18457226000181-1-000015/2023",
            "numeroControlePNCPAta": "18457226000181-1-000015/2023-000001",
            "anoAta": 2023,
        }

        ata2 = {
            "cnpjOrgao": "18457226000181",
            "numeroControlePNCPCompra": "18457226000181-1-000016/2023",
            "numeroControlePNCPAta": "18457226000181-1-000016/2023-000002",
            "anoAta": 2023,
        }

        with (
            patch(
                "pncp.extracao.consultar_detalhes_ata",
                side_effect=[
                    requests.HTTPError("Erro HTTP 500"),
                    {"numeroAtaRegistroPreco": "NPERP 004/2023"},
                ],
            ) as mock_detalhes,
            patch(
                "pncp.extracao.consultar_itens_contratacao",
                return_value=[],
            ),
        ):
            resultado = extrair_dados_complementares([ata1, ata2])

        self.assertEqual(len(resultado), 2)

        self.assertEqual(len(resultado[0]["erros"]), 1)
        self.assertEqual(resultado[0]["erros"][0]["etapa"], "detalhes")

        self.assertEqual(resultado[1]["erros"], [])
        self.assertIsNotNone(resultado[1]["detalhes"])

        self.assertEqual(mock_detalhes.call_count, 2)



if __name__ == "__main__":
    unittest.main(verbosity=2)