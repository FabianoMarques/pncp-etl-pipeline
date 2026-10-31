import logging
import time
from datetime import datetime

import requests


# Configura o logger utilizado para registrar os eventos da extração.
logger = logging.getLogger(__name__)

# Endpoint público do PNCP responsável pela consulta de atas.
URL_PNCP = "https://pncp.gov.br/api/consulta/v1/atas"

# Tempo máximo de espera por resposta em cada requisição HTTP, em segundos.
TIMEOUT = 60

# Quantidade máxima de tentativas para cada requisição.
MAX_TENTATIVAS = 3

# Intervalo inicial entre as tentativas, em segundos.
INTERVALO_INICIAL = 2

# Intervalo mínimo entre as requisições realizadas à API.
INTERVALO_REQUISICOES = 1


def validar_datas(data_inicial: str, data_final: str) -> None:
    """
    Valida as datas informadas para a consulta.

    As datas devem estar no formato AAAAMMDD, e a data inicial
    não pode ser posterior à data final.

    Args:
        data_inicial: Data inicial da consulta no formato AAAAMMDD.
        data_final: Data final da consulta no formato AAAAMMDD.

    Raises:
        ValueError: Se alguma data for inválida ou se o período
            informado estiver incorreto.
    """

    try:
        inicio = datetime.strptime(data_inicial, "%Y%m%d").date()
        fim = datetime.strptime(data_final, "%Y%m%d").date()

    except ValueError as erro:
        raise ValueError(
            "As datas devem estar no formato AAAAMMDD, "
            "por exemplo, 20261001."
        ) from erro

    # Impede consultas com um período invertido.
    if inicio > fim:
        raise ValueError(
            "A data inicial não pode ser posterior à data final."
        )


def realizar_requisicao(
    sessao: requests.Session,
    parametros: dict,
    url: str = URL_PNCP,
) -> dict:
    """
    Executa uma requisição HTTP ao PNCP com retentativas controladas.

    Erros transitórios de conexão, timeout e respostas HTTP 429
    ou 5xx podem provocar novas tentativas.

    Args:
        sessao: Sessão HTTP utilizada para realizar a requisição.
        parametros: Parâmetros enviados ao endpoint do PNCP.

    Returns:
        Dicionário contendo a resposta JSON da API.

    Raises:
        requests.RequestException: Se a requisição falhar após
            as tentativas permitidas.
        ValueError: Se a resposta não contiver um objeto JSON válido.
    """

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resposta = sessao.get(
                url,
                params=parametros,
                timeout=TIMEOUT,
            )

            # Identifica respostas HTTP que podem ser transitórias.
            if resposta.status_code == 429 or resposta.status_code >= 500:
                resposta.raise_for_status()

            # Interrompe imediatamente para erros HTTP permanentes.
            if 400 <= resposta.status_code < 500:
                resposta.raise_for_status()

            # Converte o conteúdo recebido em um objeto Python.
            dados = resposta.json()

            # A API deve retornar um objeto JSON, e não uma lista ou
            # um valor simples na raiz da resposta.
            if not isinstance(dados, (dict, list)):
                raise ValueError(
                    "Formato inesperado: a resposta da API não é um objeto ou lista JSON."
                )

            return dados

        except requests.exceptions.JSONDecodeError:
            # Registra a resposta inválida e interrompe a operação,
            # pois repetir a mesma resposta não garante uma correção.
            logger.exception(
                "Resposta JSON inválida na página %s.",
                parametros.get("pagina"),
            )
            raise

        except requests.HTTPError as erro:
            status = (
                erro.response.status_code
                if erro.response is not None
                else None
            )

            # Erros HTTP permanentes não devem ser repetidos.
            if status is not None and 400 <= status < 500 and status != 429:
                logger.error(
                    "Erro HTTP permanente na página %s: %s.",
                    parametros.get("pagina"),
                    status,
                )
                raise

            # Erros HTTP transitórios seguem para o tratamento
            # de retentativas abaixo.
            logger.warning(
                "Falha HTTP na página %s. "
                "Tentativa %s de %s. Erro: %s",
                parametros.get("pagina"),
                tentativa,
                MAX_TENTATIVAS,
                erro,
            )

            if tentativa == MAX_TENTATIVAS:
                logger.error(
                    "Limite de tentativas atingido para a página %s.",
                    parametros.get("pagina"),
                )
                raise

            if status == 429 and erro.response is not None:
                tempo_espera = erro.response.headers.get("Retry-After")

                try:
                    tempo_espera = max(0, int(tempo_espera))
                except (TypeError, ValueError):
                    tempo_espera = INTERVALO_INICIAL * (2 ** (tentativa - 1))
            else:
                tempo_espera = INTERVALO_INICIAL * (2 ** (tentativa - 1))

            logger.info("Nova tentativa em %s segundos.", tempo_espera)
            time.sleep(tempo_espera)

       
        except requests.RequestException as erro:
            logger.warning(
                "Falha na requisição da página %s. "
                "Tentativa %s de %s. Erro: %s",
                parametros.get("pagina"),
                tentativa,
                MAX_TENTATIVAS,
                erro,
            )

            if tentativa == MAX_TENTATIVAS:
                logger.error(
                    "Limite de tentativas atingido para a página %s.",
                    parametros.get("pagina"),
                )
                raise

            tempo_espera = INTERVALO_INICIAL * (2 ** (tentativa - 1))

            logger.info(
                "Nova tentativa em %s segundos.",
                tempo_espera,
            )

            time.sleep(tempo_espera)

        except ValueError:
            # Respostas JSON inválidas ou com formato inesperado
            # não são repetidas automaticamente.
            logger.exception(
                "Resposta inválida da API na página %s.",
                parametros.get("pagina"),
            )
            raise

    # Este ponto não deve ser alcançado, pois o laço retorna ou gera erro.
    raise RuntimeError("A requisição terminou sem retornar uma resposta.")


def extrair_atas(
    data_inicial: str,
    data_final: str,
    tamanho_pagina: int = 10,
    max_paginas: int | None = None,
) -> list[dict]:
    """
    Extrai atas de registro de preços da API pública do PNCP.

    A função valida o período, percorre as páginas disponíveis e
    reúne os registros retornados pela API.

    Args:
        data_inicial: Data inicial no formato AAAAMMDD.
        data_final: Data final no formato AAAAMMDD.
        tamanho_pagina: Quantidade de registros solicitados por página.
        max_paginas: Limite opcional de páginas, útil para testes.

    Returns:
        Lista de dicionários contendo os registros extraídos.

    Raises:
        ValueError: Se os parâmetros ou a estrutura da resposta
            forem inválidos.
        requests.RequestException: Se ocorrer uma falha HTTP ou de
            conexão que não puder ser resolvida pelas retentativas.
    """

    # Valida o período antes de iniciar as chamadas HTTP.
    validar_datas(data_inicial, data_final)

    if tamanho_pagina < 1:
        raise ValueError(
            "O tamanho da página deve ser maior que zero."
        )

    if max_paginas is not None and max_paginas < 1:
        raise ValueError(
            "O limite de páginas deve ser maior que zero."
        )

    # Armazena todos os registros obtidos durante a paginação.
    registros = []

    # A API utiliza numeração de páginas iniciada em 1.
    pagina = 1
    total_paginas = None

    with requests.Session() as sessao:
        while True:

            # Permite limitar a extração durante os testes.
            if max_paginas is not None and pagina > max_paginas:
                break

            # Define os parâmetros enviados ao endpoint.
            parametros = {
                "dataInicial": data_inicial,
                "dataFinal": data_final,
                "pagina": pagina,
                "tamanhoPagina": tamanho_pagina,
            }

            logger.info(
                "Consultando PNCP: página %s, período %s a %s",
                pagina,
                data_inicial,
                data_final,
            )

            # Executa a consulta com timeout e retentativas controladas.
            dados = realizar_requisicao(sessao, parametros)

            # Confere se a API retornou a lista de registros esperada.
            itens = dados.get("data")

            if not isinstance(itens, list):
                raise ValueError(
                    "Formato inesperado: o campo 'data' "
                    "não contém uma lista."
                )

            # Cada elemento da lista deve representar um registro.
            if not all(isinstance(item, dict) for item in itens):
                raise ValueError(
                    "A resposta contém registros em formato inválido."
                )

            # Obtém o total de páginas informado pela API.
            if total_paginas is None:
                total = dados.get("totalPaginas")

                if total is not None:
                    try:
                        total_paginas = int(total)
                    except (ValueError, TypeError) as erro:
                        raise ValueError(
                            "O campo 'totalPaginas' retornado "
                            "pela API é inválido."
                        ) from erro

                    if total_paginas < 0:
                        raise ValueError(
                            "O campo 'totalPaginas' não pode ser negativo."
                        )

            # Adiciona os registros da página ao resultado acumulado.
            registros.extend(itens)

            logger.info(
                "Página %s: %s registros recebidos.",
                pagina,
                len(itens),
            )

            # Encerra quando não há mais registros.
            if not itens:
                break

            # Encerra quando a última página informada foi processada.
            if total_paginas is not None and pagina >= total_paginas:
                break

            # Sem o total de páginas, uma página incompleta indica o fim.
            if total_paginas is None and len(itens) < tamanho_pagina:
                break

            # Aguarda antes de realizar a próxima requisição.
            time.sleep(INTERVALO_REQUISICOES)

            pagina += 1

    logger.info(
        "Extração concluída: %s registros.",
        len(registros),
    )

    return registros


def consultar_detalhes_ata(
    cnpj: str,
    ano: int,
    sequencial_compra: int,
    sequencial_ata: int,
) -> dict:
    """
    Consulta os detalhes de uma ata de registro de preços no PNCP.

    Args:
        cnpj: CNPJ do órgão responsável pela contratação.
        ano: Ano da contratação.
        sequencial_compra: Número sequencial da contratação.
        sequencial_ata: Número sequencial da ata.

    Returns:
        Dicionário contendo os detalhes da ata.
    """

    url = (
        f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}"
        f"/compras/{ano}/{sequencial_compra}/atas/{sequencial_ata}"
    )

    parametros = {}

    logger.info(
        "Consultando detalhes da ata: %s/%s/%s/%s",
        cnpj,
        ano,
        sequencial_compra,
        sequencial_ata,
    )

    with requests.Session() as sessao:
        dados = realizar_requisicao(
            sessao,
            parametros,
            url=url,
        )

    logger.info("Detalhes da ata consultados com sucesso.")

    return dados


def consultar_itens_contratacao(
    cnpj: str,
    ano: int,
    sequencial_compra: int,
    tamanho_pagina: int = 100,
) -> list[dict]:
    """
    Consulta todos os itens vinculados a uma contratação no PNCP.

    A consulta utiliza paginação para recuperar todos os itens.

    Args:
        cnpj: CNPJ do órgão responsável pela contratação.
        ano: Ano da contratação.
        sequencial_compra: Número sequencial da contratação.
        tamanho_pagina: Quantidade de itens por página.

    Returns:
        Lista contendo os itens da contratação.
    """

    if tamanho_pagina <= 0:
        raise ValueError("O tamanho da página deve ser maior que zero.")

    url = (
        f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}"
        f"/compras/{ano}/{sequencial_compra}/itens"
    )

    itens = []
    pagina = 1

    with requests.Session() as sessao:

        while True:

            parametros = {
                "pagina": pagina,
                "tamanhoPagina": tamanho_pagina,
            }

            logger.info(
                "Consultando itens da contratação. Página: %s",
                pagina,
            )

            dados = realizar_requisicao(
                sessao,
                parametros,
                url=url,
            )

            if not isinstance(dados, list):
                raise ValueError(
                    "A resposta do endpoint de itens não é uma lista."
                )

            if not dados:
                break

            if not all(isinstance(item, dict) for item in dados):
                raise ValueError(
                    "A resposta contém itens em formato inválido."
                )

            itens.extend(dados)

            logger.info(
                "Página %s: %s itens extraídos.",
                pagina,
                len(dados),
            )

            if len(dados) < tamanho_pagina:
                break

            pagina += 1

            time.sleep(INTERVALO_REQUISICOES)

    logger.info(
        "Consulta de itens concluída. Total extraído: %s",
        len(itens),
    )

    return itens


def consultar_resultados_item(
    cnpj: str,
    ano: int,
    sequencial_compra: int,
    numero_item: int,
) -> list[dict]:
    """
    Consulta os resultados homologados de um item da contratação.

    Args:
        cnpj: CNPJ do órgão responsável.
        ano: Ano da contratação.
        sequencial_compra: Número sequencial da contratação.
        numero_item: Número do item.

    Returns:
        Lista contendo os resultados do item.
    """

    url = (
        f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}"
        f"/compras/{ano}/{sequencial_compra}"
        f"/itens/{numero_item}/resultados"
    )

    parametros = {}

    logger.info(
        "Consultando resultados do item %s da contratação %s/%s.",
        numero_item,
        ano,
        sequencial_compra,
    )

    with requests.Session() as sessao:
        dados = realizar_requisicao(
            sessao,
            parametros,
            url=url,
        )

    if not isinstance(dados, list):
        raise ValueError(
            "A resposta do endpoint de resultados não é uma lista."
        )

    if not all(isinstance(resultado, dict) for resultado in dados):
        raise ValueError(
            "A resposta contém resultados em formato inválido."
        )

    logger.info(
        "Item %s: %s resultados encontrados.",
        numero_item,
        len(dados),
    )

    return dados


def extrair_dados_complementares(
    atas: list[dict],
    tamanho_pagina_itens: int = 100,
) -> list[dict]:
    """
    Coordena a extração dos dados complementares das atas.

    Para cada ata, consulta seus detalhes, os itens da contratação
    e os resultados dos itens que possuem resultado informado.

    Args:
        atas: Lista de atas retornadas por extrair_atas().
        tamanho_pagina_itens: Quantidade de itens por página.

    Returns:
        Lista contendo as atas e seus respectivos dados complementares.
    """

    if not isinstance(atas, list):
        raise ValueError("A entrada deve ser uma lista de atas.")

    if tamanho_pagina_itens <= 0:
        raise ValueError(
            "O tamanho da página deve ser maior que zero."
        )

    dados_complementares = []

    for indice, ata in enumerate(atas, start=1):

        if not isinstance(ata, dict):
            raise ValueError(
                f"A ata na posição {indice} possui formato inválido."
            )

        # Recupera os identificadores da contratação e da ata.
        cnpj = ata.get("cnpjOrgao")
        controle_compra = ata.get("numeroControlePNCPCompra")
        controle_ata = ata.get("numeroControlePNCPAta")
        ano_ata = ata.get("anoAta")

        if not all([
            cnpj,
            controle_compra,
            controle_ata,
            ano_ata,
        ]):
            raise ValueError(
                f"Identificadores incompletos na ata da posição {indice}."
            )

        try:
            # Extrai o sequencial da contratação.
            prefixo_compra, ano_compra = controle_compra.split("/")
            sequencial_compra = int(
                prefixo_compra.rsplit("-", 1)[1]
            )

            # Extrai o ano e o sequencial da ata.
            ano_controle_ata, sequencial_ata = (
                controle_ata.rsplit("/", 1)[1].split("-", 1)
            )

            sequencial_ata = int(sequencial_ata)

            if ano_compra != ano_controle_ata:
                raise ValueError(
                    "O ano da contratação diverge entre os identificadores."
                )

        except (ValueError, IndexError) as erro:
            raise ValueError(
                f"Não foi possível interpretar os identificadores "
                f"da ata na posição {indice}."
            ) from erro

        logger.info(
            "Iniciando extração complementar da ata %s de %s.",
            indice,
            len(atas),
        )

        # Consulta os detalhes da ata.
        erros = []

        try:
            detalhes = consultar_detalhes_ata(
                cnpj=cnpj,
                ano=int(ano_compra),
                sequencial_compra=sequencial_compra,
                sequencial_ata=sequencial_ata,
            )

        except requests.exceptions.RequestException as erro:
            detalhes = None

            erros.append({
                "etapa": "detalhes",
                "mensagem": str(erro),
            })

            logger.exception(
                "Falha ao consultar detalhes da ata %s.",
                indice,
            )

      
        # Consulta todos os itens da contratação.
        try:
            itens = consultar_itens_contratacao(
                cnpj=cnpj,
                ano=int(ano_compra),
                sequencial_compra=sequencial_compra,
                tamanho_pagina=tamanho_pagina_itens,
            )

        except requests.exceptions.RequestException as erro:
            itens = []

            erros.append({
                "etapa": "itens",
                "mensagem": str(erro),
            })

            logger.exception(
                "Falha ao consultar itens da ata %s.",
                indice,
            )

        itens_com_resultados = []

        # Consulta os resultados dos itens que possuem resultado.
        for item in itens:

            numero_item = item.get("numeroItem")

            erros_item = []

            if item.get("temResultado") is True:

                try:
                    resultados = consultar_resultados_item(
                        cnpj=cnpj,
                        ano=int(ano_compra),
                        sequencial_compra=sequencial_compra,
                        numero_item=int(numero_item),
                    )

                except requests.exceptions.RequestException as erro:
                    resultados = []

                    erros_item.append({
                        "etapa": "resultados",
                        "mensagem": str(erro),
                    })

                    logger.exception(
                        "Falha ao consultar resultados do item %s da ata %s.",
                        numero_item,
                        indice,
                    )

            else:
                resultados = []

            itens_com_resultados.append({
                    "item": item,
                    "resultados": resultados,
                    "erros": erros_item,
            })

        # Organiza os dados da ata.
        dados_complementares.append({
            "ata": ata,
            "detalhes": detalhes,
            "itens": itens_com_resultados,
            "erros": erros,
        })

        logger.info(
            "Ata %s processada: %s itens encontrados.",
            indice,
            len(itens),
        )

    logger.info(
        "Extração complementar concluída: %s atas processadas.",
        len(dados_complementares),
    )

    return dados_complementares