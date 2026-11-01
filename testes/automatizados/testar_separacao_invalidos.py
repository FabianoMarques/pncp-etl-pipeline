import unittest
import pandas as pd
from pncp.validacao import separar_itens_invalidos
from pncp.validacao import separar_atas_invalidas
from pncp.validacao import separar_resultados_invalidos


class TestSepararAtasInvalidas(unittest.TestCase):

    def setUp(self):
        self.df_atas = pd.DataFrame({
            "numeroControlePNCPAta": [
                "12345678901234-1-000001/2026-000001",
                "12345678901234-1-000002/2026-000002",
                "IDENTIFICADOR_INVALIDO",
                None,
            ],
            "cancelado": [
                False,
                True,
                False,
                False,
            ],
        })

    def test_separar_atas_validas_e_invalidas(self):
        validas, invalidas, relatorio = (
            separar_atas_invalidas(self.df_atas)
        )

        self.assertEqual(len(validas), 2)
        self.assertEqual(len(invalidas), 2)

        self.assertEqual(
            len(validas) + len(invalidas),
            len(self.df_atas),
        )

    def test_identificar_identificador_fora_do_padrao(self):
        _, invalidas, _ = separar_atas_invalidas(self.df_atas)

        self.assertIn(
            "Identificador fora do padrão esperado.",
            invalidas.iloc[0]["motivos_invalidade"],
        )

    def test_identificar_identificador_ausente(self):
        _, invalidas, _ = separar_atas_invalidas(self.df_atas)

        self.assertIn(
            "Identificador ausente ou inválido.",
            invalidas.iloc[1]["motivos_invalidade"],
        )

    def test_identificar_atas_duplicadas(self):
        df = pd.DataFrame({
            "numeroControlePNCPAta": [
                "12345678901234-1-000001/2026-000001",
                "12345678901234-1-000001/2026-000001",
            ],
            "cancelado": [False, False],
        })

        validas, invalidas, relatorio = separar_atas_invalidas(df)

        self.assertEqual(len(validas), 0)
        self.assertEqual(len(invalidas), 2)

        self.assertTrue(
            invalidas["motivos_invalidade"].str.contains(
                "Identificador de ata duplicado."
            ).all()
        )

    def test_gerar_relatorio_detalhado(self):
        _, invalidas, relatorio = separar_atas_invalidas(
            self.df_atas
        )

        self.assertFalse(relatorio.empty)

        self.assertIn("indice_origem", relatorio.columns)
        self.assertIn("numeroControlePNCPAta", relatorio.columns)
        self.assertIn("motivo", relatorio.columns)

        self.assertEqual(
            len(relatorio),
            sum(
                len(motivos.split("; "))
                for motivos in invalidas["motivos_invalidade"]
            ),
        )

    def test_preservar_indices_originais(self):
        _, invalidas, relatorio = separar_atas_invalidas(
            self.df_atas
        )

        self.assertEqual(list(invalidas.index), [2, 3])
        self.assertEqual(
            sorted(relatorio["indice_origem"].unique()),
            [2, 3],
        )


class TestSepararItensInvalidos(unittest.TestCase):

    def setUp(self):
        self.df_itens = pd.DataFrame({
            "numeroControlePNCPAta": [
                "ATA001",
                "ATA002",
                "ATA003",
                "ATA004",
                "ATA005",
            ],
            "numeroItem": pd.Series(
                [1, 2, None, 0, 5],
                dtype="object",
            ),
        })

    def test_separar_itens_validos_e_invalidos(self):
        validos, invalidos, relatorio = (
            separar_itens_invalidos(self.df_itens)
        )

        self.assertEqual(len(validos), 3)
        self.assertEqual(len(invalidos), 2)
        self.assertEqual(
            len(validos) + len(invalidos),
            len(self.df_itens),
        )

    def test_identificar_identificador_ausente(self):
        df = self.df_itens.copy()
        df.loc[0, "numeroControlePNCPAta"] = None

        _, invalidos, _ = separar_itens_invalidos(df)

        self.assertIn(
            "Identificador da ata ausente ou inválido.",
            invalidos.iloc[0]["motivos_invalidade"],
        )

    def test_identificar_numero_item_ausente(self):
        _, invalidos, _ = separar_itens_invalidos(self.df_itens)

        self.assertIn(
            "Número do item ausente.",
            invalidos.loc[2, "motivos_invalidade"],
        )

    def test_identificar_numero_item_nao_positivo(self):
        _, invalidos, _ = separar_itens_invalidos(self.df_itens)

        self.assertIn(
            "Número do item deve ser um inteiro positivo.",
            invalidos.loc[3, "motivos_invalidade"],
        )

    def test_identificar_chave_composta_duplicada(self):
        df = pd.DataFrame({
            "numeroControlePNCPAta": ["ATA001", "ATA001"],
            "numeroItem": [1, 1],
        })

        validos, invalidos, _ = separar_itens_invalidos(df)

        self.assertEqual(len(validos), 0)
        self.assertEqual(len(invalidos), 2)

        self.assertTrue(
            invalidos["motivos_invalidade"].str.contains(
                "Chave composta do item duplicada."
            ).all()
        )

    def test_gerar_relatorio_detalhado(self):
        _, invalidos, relatorio = separar_itens_invalidos(
            self.df_itens
        )

        self.assertFalse(relatorio.empty)

        self.assertIn("indice_origem", relatorio.columns)
        self.assertIn("numeroControlePNCPAta", relatorio.columns)
        self.assertIn("numeroItem", relatorio.columns)
        self.assertIn("motivo", relatorio.columns)

        self.assertEqual(
            set(relatorio["indice_origem"]),
            set(invalidos.index),
        )

    def test_preservar_indices_originais(self):
        _, invalidos, relatorio = separar_itens_invalidos(
            self.df_itens
        )

        self.assertEqual(list(invalidos.index), [2, 3])
        self.assertEqual(
            sorted(relatorio["indice_origem"].unique()),
            [2, 3],
        )

class TestSepararResultadosInvalidos(unittest.TestCase):

    def setUp(self):
        self.df_resultados = pd.DataFrame({
            "numeroControlePNCPAta": [
                "ATA001",
                "ATA002",
                "ATA003",
                "ATA004",
                "ATA005",
            ],
            "numeroItem": pd.Series(
                [1, 2, 3, 0, 5],
                dtype="object",
            ),
            "numeroItemOrigem": pd.Series(
                [1, 2, 3, 4, 5],
                dtype="object",
            ),
            "sequencialResultado": pd.Series(
                [1, 1, 1, 1, 1],
                dtype="object",
            ),
        })

    def test_separar_resultados_validos_e_invalidos(self):
        validos, invalidos, relatorio = (
            separar_resultados_invalidos(self.df_resultados)
        )

        self.assertEqual(len(validos), 4)
        self.assertEqual(len(invalidos), 1)

        self.assertEqual(
            len(validos) + len(invalidos),
            len(self.df_resultados),
        )

    def test_identificar_identificador_ausente(self):
        df = self.df_resultados.copy()
        df.loc[0, "numeroControlePNCPAta"] = None

        _, invalidos, _ = separar_resultados_invalidos(df)

        self.assertIn(
            "Identificador da ata ausente ou inválido.",
            invalidos.loc[0, "motivos_invalidade"],
        )

    def test_identificar_numero_item_ausente(self):
        df = self.df_resultados.copy()
        df.at[0, "numeroItem"] = None

        _, invalidos, _ = separar_resultados_invalidos(df)

        self.assertIn(
            "Número do item ausente.",
            invalidos.loc[0, "motivos_invalidade"],
        )

    def test_identificar_numero_item_origem_ausente(self):
        df = self.df_resultados.copy()
        df.at[0, "numeroItemOrigem"] = None

        _, invalidos, _ = separar_resultados_invalidos(df)

        self.assertIn(
            "Número do item de origem ausente.",
            invalidos.loc[0, "motivos_invalidade"],
        )

    def test_identificar_numero_item_divergente(self):
        df = self.df_resultados.copy()
        df.at[0, "numeroItemOrigem"] = 2

        _, invalidos, _ = separar_resultados_invalidos(df)

        self.assertIn(
            "Número do item divergente do número do item de origem.",
            invalidos.loc[0, "motivos_invalidade"],
        )

    def test_identificar_sequencial_ausente(self):
        df = self.df_resultados.copy()
        df.at[0, "sequencialResultado"] = None

        _, invalidos, _ = separar_resultados_invalidos(df)

        self.assertIn(
            "Sequencial do resultado ausente.",
            invalidos.loc[0, "motivos_invalidade"],
        )

    def test_identificar_chave_composta_duplicada(self):
        df = pd.concat(
            [self.df_resultados.iloc[[0]]] * 2,
            ignore_index=True,
        )

        validos, invalidos, _ = separar_resultados_invalidos(df)

        self.assertEqual(len(validos), 0)
        self.assertEqual(len(invalidos), 2)

        self.assertTrue(
            invalidos["motivos_invalidade"].str.contains(
                "Chave composta do resultado duplicada."
            ).all()
        )

    def test_gerar_relatorio_detalhado(self):
        _, invalidos, relatorio = (
            separar_resultados_invalidos(self.df_resultados)
        )

        self.assertFalse(relatorio.empty)

        self.assertIn("indice_origem", relatorio.columns)
        self.assertIn("numeroControlePNCPAta", relatorio.columns)
        self.assertIn("numeroItem", relatorio.columns)
        self.assertIn("sequencialResultado", relatorio.columns)
        self.assertIn("motivo", relatorio.columns)

    def test_preservar_indices_originais(self):
        _, invalidos, relatorio = (
            separar_resultados_invalidos(self.df_resultados)
        )

        self.assertEqual(list(invalidos.index), [3])
        self.assertEqual(
            sorted(relatorio["indice_origem"].unique()),
            [3],
        )
        

if __name__ == "__main__":
    unittest.main()