import os
import pandas as pd
import psycopg2
from datetime import datetime, timezone
from psycopg2.extras import Json
from dotenv import load_dotenv
from pncp.transformacao import ler_json
from pncp.transformacao import ler_json, criar_dataframes


def conectar_banco():

    load_dotenv(override=True)

    conexao = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    return conexao


def tratar_valor(valor):

    if pd.isna(valor):
        return None

    if hasattr(valor, "item"):
        return valor.item()

    return valor


def tratar_data(valor):

    valor = tratar_valor(valor)

    if valor is None:
        return None

    return valor


def registrar_coleta(conexao, periodo_inicio, periodo_fim):

    sql = """
        INSERT INTO pncp_coletas (
            periodo_inicio,
            periodo_fim,
            data_inicio,
            status
        )
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """

    with conexao.cursor() as cursor:

        cursor.execute(
            sql,
            (
                periodo_inicio,
                periodo_fim,
                datetime.now(timezone.utc),
                "EM_ANDAMENTO"
            )
        )

        coleta_id = cursor.fetchone()[0]

    return coleta_id


def finalizar_coleta(conexao, coleta_id, quantidade_atas):

    with conexao.cursor() as cursor:

        cursor.execute("""
            UPDATE pncp_coletas
            SET
                status = 'CONCLUIDA',
                data_fim = %s,
                quantidade_atas = %s
            WHERE id = %s
        """, (
            datetime.now(timezone.utc),
            quantidade_atas,
            coleta_id
        ))


def registrar_erro_coleta(conexao_erro, coleta_id, erro):

    with conexao_erro.cursor() as cursor:

        cursor.execute("""
            UPDATE pncp_coletas
            SET
                status = 'ERRO',
                data_fim = %s,
                mensagem_erro = %s
            WHERE id = %s
        """, (
            datetime.now(timezone.utc),
            str(erro),
            coleta_id
        ))


def inserir_staging(conexao, coleta_id, registros):

    sql = """
        INSERT INTO stg_pncp_registros (
            coleta_id,
            numero_controle_pncp_ata,
            dados_originais,
            data_coleta
        )
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)

        ON CONFLICT (coleta_id, numero_controle_pncp_ata)
        DO UPDATE SET
            dados_originais = EXCLUDED.dados_originais,
            data_coleta = CURRENT_TIMESTAMP;
    """

    total_inseridos = 0

    with conexao.cursor() as cursor:

        for registro in registros:

            ata = registro.get("ata", {})

            numero_controle = ata.get("numeroControlePNCPAta")

            if not numero_controle:
                continue

            cursor.execute(
                sql,
                (
                    coleta_id,
                    numero_controle,
                    Json(registro)
                )
            )
            total_inseridos += 1

    return total_inseridos



def inserir_atas(conexao, coleta_id, df_atas):

    sql = """
        INSERT INTO pncp_atas (
            numero_controle_pncp_ata,
            numero_ata_registro_preco,
            ano_ata,
            numero_controle_pncp_compra,
            cnpj_orgao,
            nome_orgao,
            objeto_contratacao,
            cancelado,
            data_cancelamento,
            data_assinatura,
            vigencia_inicio,
            vigencia_fim,
            data_publicacao_pncp,
            data_inclusao_pncp,
            data_atualizacao_pncp,
            ultima_coleta_id,
            data_coleta,
            data_atualizacao
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT (numero_controle_pncp_ata)
        DO UPDATE SET
            numero_ata_registro_preco = EXCLUDED.numero_ata_registro_preco,
            ano_ata = EXCLUDED.ano_ata,
            numero_controle_pncp_compra = EXCLUDED.numero_controle_pncp_compra,
            cnpj_orgao = EXCLUDED.cnpj_orgao,
            nome_orgao = EXCLUDED.nome_orgao,
            objeto_contratacao = EXCLUDED.objeto_contratacao,
            cancelado = EXCLUDED.cancelado,
            data_cancelamento = EXCLUDED.data_cancelamento,
            data_assinatura = EXCLUDED.data_assinatura,
            vigencia_inicio = EXCLUDED.vigencia_inicio,
            vigencia_fim = EXCLUDED.vigencia_fim,
            data_publicacao_pncp = EXCLUDED.data_publicacao_pncp,
            data_inclusao_pncp = EXCLUDED.data_inclusao_pncp,
            data_atualizacao_pncp = EXCLUDED.data_atualizacao_pncp,
            ultima_coleta_id = EXCLUDED.ultima_coleta_id,
            data_atualizacao = CURRENT_TIMESTAMP;
    """

    total = 0

    with conexao.cursor() as cursor:

        for _, ata in df_atas.iterrows():

            valores = (
                ata["numeroControlePNCPAta"],
                tratar_valor(ata["numeroAtaRegistroPreco"]),
                tratar_valor(ata["anoAta"]),
                tratar_valor(ata["numeroControlePNCPCompra"]),
                tratar_valor(ata["cnpjOrgao"]),
                tratar_valor(ata["nomeOrgao"]),
                tratar_valor(ata["objetoContratacao"]),
                tratar_valor(ata["cancelado"]),
                tratar_valor(ata["dataCancelamento"]),
                tratar_valor(ata["dataAssinatura"]),
                tratar_valor(ata["vigenciaInicio"]),
                tratar_valor(ata["vigenciaFim"]),
                tratar_valor(ata["dataPublicacaoPncp"]),
                tratar_valor(ata["dataInclusao"]),
                tratar_valor(ata["dataAtualizacao"]),
                coleta_id
            )

            cursor.execute(sql, valores)

            total += 1

    return total



def inserir_itens(conexao, coleta_id, df_itens):

    sql_buscar_ata = """
        SELECT id
        FROM pncp_atas
        WHERE numero_controle_pncp_ata = %s;
    """

    sql_inserir = """
        INSERT INTO pncp_itens (
            ata_id,
            numero_item,
            descricao,
            material_ou_servico,
            valor_unitario_estimado,
            valor_total,
            quantidade,
            unidade_medida,
            situacao_compra_item,
            situacao_compra_item_nome,
            tem_resultado,
            data_inclusao_pncp,
            data_atualizacao_pncp,
            ultima_coleta_id,
            data_coleta,
            data_atualizacao
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ata_id, numero_item)
        DO UPDATE SET
            descricao = EXCLUDED.descricao,
            material_ou_servico = EXCLUDED.material_ou_servico,
            valor_unitario_estimado = EXCLUDED.valor_unitario_estimado,
            valor_total = EXCLUDED.valor_total,
            quantidade = EXCLUDED.quantidade,
            unidade_medida = EXCLUDED.unidade_medida,
            situacao_compra_item = EXCLUDED.situacao_compra_item,
            situacao_compra_item_nome = EXCLUDED.situacao_compra_item_nome,
            tem_resultado = EXCLUDED.tem_resultado,
            data_inclusao_pncp = EXCLUDED.data_inclusao_pncp,
            data_atualizacao_pncp = EXCLUDED.data_atualizacao_pncp,
            ultima_coleta_id = EXCLUDED.ultima_coleta_id,
            data_atualizacao = CURRENT_TIMESTAMP;
    """

    total = 0

    with conexao.cursor() as cursor:

        for _, item in df_itens.iterrows():

            cursor.execute(
                sql_buscar_ata,
                (item["numeroControlePNCPAta"],)
            )

            resultado = cursor.fetchone()

            if resultado is None:
                raise ValueError(
                    f"Ata não encontrada: {item['numeroControlePNCPAta']}"
                )

            ata_id = resultado[0]

            valores = (
                ata_id,
                tratar_valor(item["numeroItem"]),
                tratar_valor(item["descricao"]),
                tratar_valor(item["materialOuServico"]),
                tratar_valor(item["valorUnitarioEstimado"]),
                tratar_valor(item["valorTotal"]),
                tratar_valor(item["quantidade"]),
                tratar_valor(item["unidadeMedida"]),
                tratar_valor(item["situacaoCompraItem"]),
                tratar_valor(item["situacaoCompraItemNome"]),
                tratar_valor(item["temResultado"]),
                tratar_valor(item["dataInclusao"]),
                tratar_valor(item["dataAtualizacao"]),
                coleta_id
            )

            cursor.execute(sql_inserir, valores)

            total += 1

    return total


def inserir_resultados(conexao, coleta_id, df_resultados):

    total = 0

    with conexao.cursor() as cursor:

        for _, linha in df_resultados.iterrows():

            # Localiza o item correspondente
            cursor.execute("""
                SELECT i.id
                FROM pncp_itens i
                JOIN pncp_atas a
                    ON a.id = i.ata_id
                WHERE a.numero_controle_pncp_ata = %s
                  AND i.numero_item = %s
            """, (
                tratar_valor(linha["numeroControlePNCPAta"]),
                tratar_valor(linha["numeroItemOrigem"])
            ))

            resultado = cursor.fetchone()

            if resultado is None:
                raise ValueError(
                    f"Item não encontrado para o resultado: "
                    f"Ata {linha['numeroControlePNCPAta']} "
                    f"Item {linha['numeroItemOrigem']}"
                )

            item_id = resultado[0]

            cursor.execute("""
                INSERT INTO pncp_resultados (
                    item_id,
                    sequencial_resultado,
                    ni_fornecedor,
                    tipo_pessoa,
                    nome_razao_social_fornecedor,
                    valor_total_homologado,
                    valor_unitario_homologado,
                    quantidade_homologada,
                    percentual_desconto,
                    data_resultado,
                    data_cancelamento,
                    data_inclusao_pncp,
                    data_atualizacao_pncp,
                    ultima_coleta_id,
                    data_coleta,
                    data_atualizacao
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                ON CONFLICT (item_id, sequencial_resultado)
                DO UPDATE SET
                    ni_fornecedor = EXCLUDED.ni_fornecedor,
                    tipo_pessoa = EXCLUDED.tipo_pessoa,
                    nome_razao_social_fornecedor = EXCLUDED.nome_razao_social_fornecedor,
                    valor_total_homologado = EXCLUDED.valor_total_homologado,
                    valor_unitario_homologado = EXCLUDED.valor_unitario_homologado,
                    quantidade_homologada = EXCLUDED.quantidade_homologada,
                    percentual_desconto = EXCLUDED.percentual_desconto,
                    data_resultado = EXCLUDED.data_resultado,
                    data_cancelamento = EXCLUDED.data_cancelamento,
                    data_inclusao_pncp = EXCLUDED.data_inclusao_pncp,
                    data_atualizacao_pncp = EXCLUDED.data_atualizacao_pncp,
                    ultima_coleta_id = EXCLUDED.ultima_coleta_id,
                    data_atualizacao = EXCLUDED.data_atualizacao
            """, (
                item_id,
                tratar_valor(linha["sequencialResultado"]),
                tratar_valor(linha["niFornecedor"]),
                tratar_valor(linha["tipoPessoa"]),
                tratar_valor(linha["nomeRazaoSocialFornecedor"]),
                tratar_valor(linha["valorTotalHomologado"]),
                tratar_valor(linha["valorUnitarioHomologado"]),
                tratar_valor(linha["quantidadeHomologada"]),
                tratar_valor(linha["percentualDesconto"]),
                tratar_valor(linha["dataResultado"]),
                tratar_valor(linha["dataCancelamento"]),
                tratar_valor(linha["dataInclusao"]),
                tratar_valor(linha["dataAtualizacao"]),
                coleta_id,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            ))

            total += 1

    return total


def executar_carga(periodo_inicio, periodo_fim):

    conexao = conectar_banco()
    coleta_id = None

    try:

        # 1. Ler os dados
        dados = ler_json()

        # 2. Transformar os dados
        df_atas, df_itens, df_resultados = criar_dataframes(dados)

        print(f"Atas identificadas: {len(df_atas)}")
        print(f"Itens identificados: {len(df_itens)}")
        print(f"Resultados identificados: {len(df_resultados)}")

        # 3. Registrar a coleta
        coleta_id = registrar_coleta(
            conexao,
            periodo_inicio,
            periodo_fim
        )

        # Confirma o registro inicial da coleta
        conexao.commit()

        print(f"Coleta registrada: {coleta_id}")

        # 4. Carregar dados originais na staging
        total_staging = inserir_staging(
            conexao,
            coleta_id,
            dados
        )

        print(f"Registros na staging: {total_staging}")

        # 5. Carregar atas
        total_atas = inserir_atas(
            conexao,
            coleta_id,
            df_atas
        )

        print(f"Atas processadas: {total_atas}")

        # 6. Carregar itens
        total_itens = inserir_itens(
            conexao,
            coleta_id,
            df_itens
        )

        print(f"Itens processados: {total_itens}")

        # 7. Carregar resultados
        total_resultados = inserir_resultados(
            conexao,
            coleta_id,
            df_resultados
        )

        print(f"Resultados processados: {total_resultados}")

        # 8. Finalizar coleta
        finalizar_coleta(
            conexao,
            coleta_id,
            total_atas
        )

        # 9. Confirmar toda a carga
        conexao.commit()

        print("Carga concluída com sucesso!")

    except Exception as erro:
        print(f"Erro durante a carga: {erro}")

        conexao.rollback()

        if coleta_id is not None:
            conexao_erro = None

            try:
                conexao_erro = conectar_banco()

                registrar_erro_coleta(
                    conexao_erro,
                    coleta_id,
                    erro
                )

                conexao_erro.commit()

            except Exception as erro_registro:
                if conexao_erro is not None:
                    conexao_erro.rollback()

                print(f"Erro ao registrar falha da coleta: {erro_registro}")

            finally:
                if conexao_erro is not None:
                    conexao_erro.close()

        raise

    finally:
        conexao.close()


if __name__ == "__main__":

    executar_carga(
        periodo_inicio="2026-10-01",
        periodo_fim="2026-10-28"
    )