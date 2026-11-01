import os
import unittest

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from pncp.carga import (
    inserir_staging,
    inserir_atas,
    inserir_itens,
    inserir_resultados
)


class TestIdempotenciaPostgreSQL(unittest.TestCase):

    def setUp(self):

        load_dotenv(override=True)

        # Conexão exclusiva com o banco de testes.
        self.conexao = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            dbname="db_pncp_test",
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )

        # Proteção adicional: impede testes no banco principal.
        with self.conexao.cursor() as cursor:
            cursor.execute("SELECT current_database();")
            banco = cursor.fetchone()[0]

        if banco != "db_pncp_test":
            self.conexao.close()
            raise RuntimeError(
                f"Banco incorreto para testes: {banco}"
            )

        # Cada teste recebe duas coletas independentes.
        self.coleta_1 = self.criar_coleta()
        self.coleta_2 = self.criar_coleta()

    def tearDown(self):

        if self.conexao:
            self.conexao.rollback()
            self.conexao.close()

    def criar_coleta(self):

        with self.conexao.cursor() as cursor:
            cursor.execute("""
                INSERT INTO pncp_coletas (
                    periodo_inicio,
                    periodo_fim
                )
                VALUES ('2026-10-01', '2026-10-28')
                RETURNING id;
            """)

            return cursor.fetchone()[0]

    def criar_dataframe_ata(self, objeto):

        return pd.DataFrame([{
            "numeroControlePNCPAta": "ATA-TESTE-001",
            "numeroAtaRegistroPreco": "001/2026",
            "anoAta": 2026,
            "numeroControlePNCPCompra": "COMPRA-001",
            "cnpjOrgao": "12345678000199",
            "nomeOrgao": "Órgão de Teste",
            "objetoContratacao": objeto,
            "cancelado": False,
            "dataCancelamento": None,
            "dataAssinatura": None,
            "vigenciaInicio": None,
            "vigenciaFim": None,
            "dataPublicacaoPncp": None,
            "dataInclusao": None,
            "dataAtualizacao": None
        }])

    def criar_dataframe_item(self, descricao):

        return pd.DataFrame([{
            "numeroControlePNCPAta": "ATA-TESTE-001",
            "numeroItem": 1,
            "descricao": descricao,
            "materialOuServico": "M",
            "valorUnitarioEstimado": 100.00,
            "valorTotal": 1000.00,
            "quantidade": 10,
            "unidadeMedida": "UN",
            "situacaoCompraItem": 1,
            "situacaoCompraItemNome": "Homologado",
            "temResultado": True,
            "dataInclusao": None,
            "dataAtualizacao": None
        }])

    def criar_dataframe_resultado(self, fornecedor):

        return pd.DataFrame([{
            "numeroControlePNCPAta": "ATA-TESTE-001",
            "numeroItemOrigem": 1,
            "sequencialResultado": 1,
            "niFornecedor": "12345678000199",
            "tipoPessoa": "PJ",
            "nomeRazaoSocialFornecedor": fornecedor,
            "valorTotalHomologado": 900.00,
            "valorUnitarioHomologado": 90.00,
            "quantidadeHomologada": 10,
            "percentualDesconto": 10.00,
            "dataResultado": None,
            "dataCancelamento": None,
            "dataInclusao": None,
            "dataAtualizacao": None
        }])

    def preparar_ata(self):

        inserir_atas(
            self.conexao,
            self.coleta_1,
            self.criar_dataframe_ata("Objeto inicial")
        )

    def preparar_item(self):

        self.preparar_ata()

        inserir_itens(
            self.conexao,
            self.coleta_1,
            self.criar_dataframe_item("Computador inicial")
        )

    def test_staging_mesma_coleta_atualiza_registro(self):

        registros_1 = [{
            "ata": {
                "numeroControlePNCPAta": "ATA-TESTE-001"
            },
            "versao": "inicial"
        }]

        registros_2 = [{
            "ata": {
                "numeroControlePNCPAta": "ATA-TESTE-001"
            },
            "versao": "atualizada"
        }]

        inserir_staging(
            self.conexao,
            self.coleta_1,
            registros_1
        )

        inserir_staging(
            self.conexao,
            self.coleta_1,
            registros_2
        )

        with self.conexao.cursor() as cursor:

            cursor.execute("""
                SELECT COUNT(*), MAX(dados_originais->>'versao')
                FROM stg_pncp_registros
                WHERE coleta_id = %s;
            """, (self.coleta_1,))

            quantidade, versao = cursor.fetchone()

        self.assertEqual(quantidade, 1)
        self.assertEqual(versao, "atualizada")

    def test_staging_nova_coleta_preserva_historico(self):

        registros = [{
            "ata": {
                "numeroControlePNCPAta": "ATA-TESTE-001"
            },
            "versao": "inicial"
        }]

        inserir_staging(
            self.conexao,
            self.coleta_1,
            registros
        )

        inserir_staging(
            self.conexao,
            self.coleta_2,
            registros
        )

        with self.conexao.cursor() as cursor:

            cursor.execute("""
                SELECT COUNT(*)
                FROM stg_pncp_registros
                WHERE numero_controle_pncp_ata = 'ATA-TESTE-001';
            """)

            quantidade = cursor.fetchone()[0]

        self.assertEqual(quantidade, 2)

    def test_atas_nao_duplicam_e_sao_atualizadas(self):

        inserir_atas(
            self.conexao,
            self.coleta_1,
            self.criar_dataframe_ata("Objeto inicial")
        )

        inserir_atas(
            self.conexao,
            self.coleta_2,
            self.criar_dataframe_ata("Objeto atualizado")
        )

        with self.conexao.cursor() as cursor:

            cursor.execute("""
                SELECT COUNT(*), MAX(objeto_contratacao),
                       MAX(ultima_coleta_id)
                FROM pncp_atas
                WHERE numero_controle_pncp_ata = 'ATA-TESTE-001';
            """)

            quantidade, objeto, coleta = cursor.fetchone()

        self.assertEqual(quantidade, 1)
        self.assertEqual(objeto, "Objeto atualizado")
        self.assertEqual(coleta, self.coleta_2)

    def test_itens_nao_duplicam_e_sao_atualizados(self):

        self.preparar_item()

        inserir_itens(
            self.conexao,
            self.coleta_2,
            self.criar_dataframe_item("Computador atualizado")
        )

        with self.conexao.cursor() as cursor:

            cursor.execute("""
                SELECT COUNT(*), MAX(descricao),
                       MAX(ultima_coleta_id)
                FROM pncp_itens;
            """)

            quantidade, descricao, coleta = cursor.fetchone()

        self.assertEqual(quantidade, 1)
        self.assertEqual(descricao, "Computador atualizado")
        self.assertEqual(coleta, self.coleta_2)

    def test_resultados_nao_duplicam_e_sao_atualizados(self):

        self.preparar_item()

        inserir_resultados(
            self.conexao,
            self.coleta_1,
            self.criar_dataframe_resultado("Fornecedor inicial")
        )

        inserir_resultados(
            self.conexao,
            self.coleta_2,
            self.criar_dataframe_resultado("Fornecedor atualizado")
        )

        with self.conexao.cursor() as cursor:

            cursor.execute("""
                SELECT COUNT(*),
                       MAX(nome_razao_social_fornecedor),
                       MAX(ultima_coleta_id)
                FROM pncp_resultados;
            """)

            quantidade, fornecedor, coleta = cursor.fetchone()

        self.assertEqual(quantidade, 1)
        self.assertEqual(fornecedor, "Fornecedor atualizado")
        self.assertEqual(coleta, self.coleta_2)


if __name__ == "__main__":
    unittest.main(verbosity=2)