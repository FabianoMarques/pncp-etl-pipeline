import unittest
import pandas as pd
import json
from unittest.mock import mock_open, patch

from pncp.transformacao import (
    criar_dataframes,
    normalizar_colunas,
    converter_datas
)

from pncp.transformacao import (
    criar_dataframes,
    normalizar_colunas,
    converter_datas,
    ler_json
)


class TestCriarDataframes(unittest.TestCase):

    def setUp(self):
        self.dados = [
            {
                "ata": {
                    "numeroControlePNCPAta": "ATA-001",
                    "numeroAtaRegistroPreco": "001/2026"
                },
                "detalhes": {
                    "orgaoEntidade": {
                        "razaoSocial": "Órgão de Teste",
                        "esferaId": "F",
                        "poderId": "E"
                    },
                    "unidadeOrgao": {
                        "municipioNome": "Fortaleza",
                        "ufSigla": "CE",
                        "codigoIbge": "2304400"
                    }
                },
                "itens": [
                    {
                        "item": {
                            "numeroItem": 1,
                            "descricao": "Computador"
                        },
                        "resultados": [
                            {
                                "numeroItem": 1,
                                "sequencialResultado": 1,
                                "quantidadeHomologada": 10
                            }
                        ]
                    }
                ]
            }
        ]

    def test_quantidade_registros(self):
        df_atas, df_itens, df_resultados = criar_dataframes(self.dados)

        self.assertEqual(len(df_atas), 1)
        self.assertEqual(len(df_itens), 1)
        self.assertEqual(len(df_resultados), 1)

    def test_identificadores_origem(self):
        df_atas, df_itens, df_resultados = criar_dataframes(self.dados)

        self.assertEqual(df_atas.iloc[0]["id_origem"], 0)
        self.assertEqual(df_itens.iloc[0]["id_origem"], 0)
        self.assertEqual(df_resultados.iloc[0]["id_origem"], 0)

    def test_relacionamento_ata_item_resultado(self):
        df_atas, df_itens, df_resultados = criar_dataframes(self.dados)

        self.assertEqual(
            df_itens.iloc[0]["numeroControlePNCPAta"],
            "ATA-001"
        )

        self.assertEqual(
            df_resultados.iloc[0]["numeroControlePNCPAta"],
            "ATA-001"
        )

        self.assertEqual(
            df_resultados.iloc[0]["numeroItemOrigem"],
            1
        )

    def test_dados_complementares_ata(self):
        df_atas, _, _ = criar_dataframes(self.dados)

        self.assertEqual(
            df_atas.iloc[0]["razaoSocialOrgao"],
            "Órgão de Teste"
        )

        self.assertEqual(
            df_atas.iloc[0]["municipioUnidade"],
            "Fortaleza"
        )

    def test_dados_vazios(self):
        df_atas, df_itens, df_resultados = criar_dataframes([])

        self.assertTrue(df_atas.empty)
        self.assertTrue(df_itens.empty)
        self.assertTrue(df_resultados.empty)

    def test_registro_com_estruturas_incompletas(self):

        dados = [
            {
                "ata": {
                    "numeroControlePNCPAta": "ATA-002"
                }
            }
        ]

        df_atas, df_itens, df_resultados = criar_dataframes(dados)

        self.assertEqual(len(df_atas), 1)
        self.assertEqual(len(df_itens), 0)
        self.assertEqual(len(df_resultados), 0)

        self.assertEqual(
            df_atas.iloc[0]["numeroControlePNCPAta"],
            "ATA-002"
        )

        self.assertTrue(
            pd.isna(df_atas.iloc[0]["razaoSocialOrgao"])
        )


class TestNormalizarColunas(unittest.TestCase):

    def test_converter_camel_case(self):
        df = pd.DataFrame(columns=[
            "numeroControlePNCPAta",
            "razaoSocialOrgao",
            "dataPublicacao"
        ])

        resultado = normalizar_colunas(df)

        self.assertEqual(
            list(resultado.columns),
            [
                "numero_controle_pncp_ata",
                "razao_social_orgao",
                "data_publicacao"
            ]
        )

    def test_preservar_dados(self):
        df = pd.DataFrame({
            "numeroItem": [1, 2],
            "descricaoItem": ["Computador", "Monitor"]
        })

        resultado = normalizar_colunas(df)

        self.assertEqual(resultado.iloc[0]["numero_item"], 1)
        self.assertEqual(
            resultado.iloc[1]["descricao_item"],
            "Monitor"
        )

    def test_dataframe_sem_colunas(self):
        df = pd.DataFrame()

        resultado = normalizar_colunas(df)

        self.assertTrue(resultado.empty)
        self.assertEqual(len(resultado.columns), 0)

class TestConverterDatas(unittest.TestCase):

    def test_converter_datas_validas(self):
        df = pd.DataFrame({
            "dataPublicacao": [
                "2026-10-01T10:30:00",
                "2026-10-15T14:00:00"
            ]
        })

        resultado = converter_datas(
            df,
            ["dataPublicacao"]
        )

        self.assertTrue(
            pd.api.types.is_datetime64_any_dtype(
                resultado["dataPublicacao"]
            )
        )

        self.assertEqual(
            resultado["dataPublicacao"].iloc[0].year,
            2026
        )

    def test_tratar_datas_invalidas(self):
        df = pd.DataFrame({
            "dataPublicacao": [
                "2026-10-01T10:30:00",
                "data-invalida",
                None
            ]
        })

        resultado = converter_datas(
            df,
            ["dataPublicacao"]
        )

        self.assertFalse(
            pd.isna(resultado["dataPublicacao"].iloc[0])
        )

        self.assertTrue(
            pd.isna(resultado["dataPublicacao"].iloc[1])
        )

        self.assertTrue(
            pd.isna(resultado["dataPublicacao"].iloc[2])
        )

    def test_coluna_inexistente(self):
        df = pd.DataFrame({
            "nome": ["Computador", "Monitor"]
        })

        resultado = converter_datas(
            df,
            ["dataPublicacao"]
        )

        self.assertIn("nome", resultado.columns)
        self.assertNotIn("dataPublicacao", resultado.columns)

        self.assertEqual(len(resultado), 2)

class TestLerJson(unittest.TestCase):

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[{"id": 1, "nome": "Ata de teste"}]'
    )
    def test_leitura_json_valido(self, mock_arquivo):

        resultado = ler_json()

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], 1)
        self.assertEqual(resultado[0]["nome"], "Ata de teste")

        mock_arquivo.assert_called_once()

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[]'
    )
    def test_leitura_json_vazio(self, mock_arquivo):

        resultado = ler_json()

        self.assertEqual(resultado, [])

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"id": 1, json inválido}'
    )
    def test_json_invalido(self, mock_arquivo):

        with self.assertRaises(json.JSONDecodeError):
            ler_json()


if __name__ == "__main__":
    unittest.main()
