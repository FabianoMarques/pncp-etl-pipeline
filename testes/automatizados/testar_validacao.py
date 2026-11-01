import unittest
from pncp.validacao import validar_registros
import pandas as pd
from pncp.validacao import validar_dataframes


class TestValidarRegistros(unittest.TestCase):

    def setUp(self):
        self.registros_validos = [
            {
                "numeroControlePNCPAta": "12345678901234-1-123456/2026-123456",
                "cancelado": False,
            },
            {
                "numeroControlePNCPAta": "98765432109876-1-654321/2026-654321",
                "cancelado": True,
            },
        ]

    def test_registros_validos(self):
        resultado = validar_registros(self.registros_validos)

        self.assertEqual(resultado, self.registros_validos)

    def test_entrada_nao_e_lista(self):
        with self.assertRaises(TypeError):
            validar_registros({"numeroControlePNCPAta": "123"})

    def test_lista_vazia(self):
        with self.assertRaises(ValueError):
            validar_registros([])

    def test_registro_nao_e_dicionario(self):
        registros = ["registro inválido"]

        with self.assertRaises(ValueError):
            validar_registros(registros)

    def test_identificador_ausente(self):
        registros = [{"cancelado": False}]

        with self.assertRaises(ValueError):
            validar_registros(registros)

    def test_identificador_vazio(self):
        registros = [
            {
                "numeroControlePNCPAta": " ",
                "cancelado": False,
            }
        ]

        with self.assertRaises(ValueError):
            validar_registros(registros)

    def test_campo_cancelado_ausente(self):
        registros = [
            {"numeroControlePNCPAta": "123"}
        ]

        with self.assertRaises(ValueError):
            validar_registros(registros)

    def test_cancelado_nao_e_booleano(self):
        registros = [
            {
                "numeroControlePNCPAta": "123",
                "cancelado": "false",
            }
        ]

        with self.assertRaises(ValueError):
            validar_registros(registros)

    def test_identificador_duplicado(self):
        registros = [
            {
                "numeroControlePNCPAta": "123",
                "cancelado": False,
            },
            {
                "numeroControlePNCPAta": "123",
                "cancelado": False,
            },
        ]

        with self.assertRaises(ValueError):
            validar_registros(registros)


class TestValidarDataframes(unittest.TestCase):

    
    def setUp(self):
        self.df_atas = pd.DataFrame([
            {
                "numeroControlePNCPAta": "12345678901234-1-123456/2026-123456",
            }
        ])

        self.df_itens = pd.DataFrame([
            {
                "numeroControlePNCPAta": "12345678901234-1-123456/2026-123456",
                "numeroItem": 1,
                "valorUnitarioEstimado": 100.0,
                "valorTotal": 200.0,
                "quantidade": 2,
            }
        ])

        self.df_resultados = pd.DataFrame([
            {
                "numeroControlePNCPAta": "12345678901234-1-123456/2026-123456",
                "numeroItem": 1,
                "numeroItemOrigem": 1,
                "sequencialResultado": 1,
                "valorUnitarioHomologado": 90.0,
                "valorTotalHomologado": 180.0,
                "quantidadeHomologada": 2,
                "percentualDesconto": 10.0,
            }
        ])

    def validar(self):
        return validar_dataframes(
            self.df_atas,
            self.df_itens,
            self.df_resultados,
        )

    def test_dataframes_validos(self):
        resultado = self.validar()

        self.assertEqual(resultado["status"], "aprovado")
        self.assertEqual(resultado["total_erros"], 0)

    def test_ata_sem_identificador(self):
        self.df_atas.loc[0, "numeroControlePNCPAta"] = None

        with self.assertRaises(ValueError):
            self.validar()

    def test_ata_com_identificador_duplicado(self):
        self.df_atas = pd.concat(
            [self.df_atas, self.df_atas],
            ignore_index=True,
        )

        with self.assertRaises(ValueError):
            self.validar()

    def test_identificador_fora_do_padrao(self):
        self.df_atas.loc[0, "numeroControlePNCPAta"] = "123456"

        with self.assertRaises(ValueError):
            self.validar()

    def test_item_sem_ata_correspondente(self):
        self.df_itens.loc[0, "numeroControlePNCPAta"] = (
            "99999999999999-1-999999/2026-999999"
        )

        with self.assertRaises(ValueError):
            self.validar()

    def test_resultado_sem_ata_correspondente(self):
        self.df_resultados.loc[0, "numeroControlePNCPAta"] = (
            "99999999999999-1-999999/2026-999999"
        )

        with self.assertRaises(ValueError):
            self.validar()

    def test_resultado_sem_item_correspondente(self):
        self.df_resultados.loc[0, "numeroItemOrigem"] = 2

        with self.assertRaises(ValueError):
            self.validar()

    def test_numero_item_nao_inteiro(self):
        self.df_itens["numeroItem"] = self.df_itens[
            "numeroItem"
        ].astype(float)

        with self.assertRaises(ValueError):
            self.validar()

    def test_numero_item_nao_positivo(self):
        self.df_itens.loc[0, "numeroItem"] = 0

        with self.assertRaises(ValueError):
            self.validar()

    def test_resultado_com_item_divergente(self):
        self.df_resultados.loc[0, "numeroItem"] = 2

        with self.assertRaises(ValueError):
            self.validar()

    def test_valor_estimado_negativo(self):
        self.df_itens.loc[0, "valorUnitarioEstimado"] = -100.0

        with self.assertRaises(ValueError):
            self.validar()

    def test_percentual_desconto_fora_do_intervalo(self):
        self.df_resultados.loc[0, "percentualDesconto"] = 120.0

        with self.assertRaises(ValueError):
            self.validar()

    def test_divergencia_valor_total_item(self):
        self.df_itens.loc[0, "valorTotal"] = 300.0

        with self.assertRaises(ValueError):
            self.validar()

    def test_divergencia_valor_total_homologado(self):
        self.df_resultados.loc[0, "valorTotalHomologado"] = 300.0

        with self.assertRaises(ValueError):
            self.validar()

    def test_item_com_valor_zerado_gera_alerta(self):
        self.df_itens.loc[0, "valorUnitarioEstimado"] = 0.0
        self.df_itens.loc[0, "valorTotal"] = 0.0

        resultado = self.validar()

        self.assertEqual(resultado["status"], "aprovado")
        self.assertEqual(resultado["total_alertas"], 1)
        self.assertTrue(resultado["alertas"])


class TestGerarRelatorioAusencias(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.caminho_relatorio = (
            f"{self.temp_dir.name}/relatorio.csv"
        )

    def test_gerar_arquivo_csv(self):
        from pncp.validacao import gerar_relatorio_ausencias

        dataframes = {
            "df_atas": pd.DataFrame({
                "data_cancelamento": [None, None],
                "campo_novo": [None, "preenchido"],
            })
        }

        gerar_relatorio_ausencias(
            dataframes=dataframes,
            arquivo_origem="dados_teste.json",
            caminho_saida=self.caminho_relatorio,
        )

        from pathlib import Path
        self.assertTrue(Path(self.caminho_relatorio).exists())

    def test_identificar_quantidade_e_percentual_ausencias(self):
        from pncp.validacao import gerar_relatorio_ausencias

        dataframes = {
            "df_atas": pd.DataFrame({
                "data_cancelamento": [None, None, "2026-10-10", None],
            })
        }

        gerar_relatorio_ausencias(
            dataframes,
            "dados_teste.json",
            self.caminho_relatorio,
        )

        relatorio = pd.read_csv(
            self.caminho_relatorio,
            sep=";",
            encoding="utf-8-sig",
        )

        registro = relatorio.iloc[0]

        self.assertEqual(registro["total_registros"], 4)
        self.assertEqual(registro["valores_ausentes"], 3)
        self.assertEqual(registro["percentual_ausencia"], 75.0)

    def test_aplicar_classificacao_definida(self):
        from pncp.validacao import gerar_relatorio_ausencias

        dataframes = {
            "df_atas": pd.DataFrame({
                "data_cancelamento": [None, None],
            })
        }

        gerar_relatorio_ausencias(
            dataframes,
            "dados_teste.json",
            self.caminho_relatorio,
        )

        relatorio = pd.read_csv(
            self.caminho_relatorio,
            sep=";",
            encoding="utf-8-sig",
        )

        self.assertEqual(
            relatorio.iloc[0]["classificacao"],
            "Ausência compatível com a situação observada",
        )

    def test_classificacao_padrao_para_campo_desconhecido(self):
        from pncp.validacao import gerar_relatorio_ausencias

        dataframes = {
            "df_atas": pd.DataFrame({
                "campo_novo": [None, "preenchido"],
            })
        }

        gerar_relatorio_ausencias(
            dataframes,
            "dados_teste.json",
            self.caminho_relatorio,
        )

        relatorio = pd.read_csv(
            self.caminho_relatorio,
            sep=";",
            encoding="utf-8-sig",
        )

        self.assertEqual(
            relatorio.iloc[0]["classificacao"],
            "Pendente de classificação",
        )

    def test_gerar_relatorio_sem_ausencias(self):
        from pncp.validacao import gerar_relatorio_ausencias

        dataframes = {
            "df_atas": pd.DataFrame({
                "data_cancelamento": ["2026-10-10", "2026-10-11"],
            })
        }

        gerar_relatorio_ausencias(
            dataframes,
            "dados_teste.json",
            self.caminho_relatorio,
        )

        relatorio = pd.read_csv(
            self.caminho_relatorio,
            sep=";",
            encoding="utf-8-sig",
        )

        self.assertEqual(len(relatorio), 0)
        self.assertIn("campo", relatorio.columns)


if __name__ == "__main__":
    unittest.main()