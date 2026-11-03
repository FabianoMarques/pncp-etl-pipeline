# Pipeline ETL — PNCP

Projeto de Engenharia de Dados para extração, transformação, validação e carga de dados de Atas de Registro de Preços do **Portal Nacional de Contratações Públicas (PNCP)**, utilizando a API pública do PNCP, Python, Apache Airflow e PostgreSQL.

## 1. Arquitetura

O fluxo é orquestrado pelo Airflow por meio da DAG `etl_pncp`:

1. **Extração:** consulta a API pública do PNCP para obter as atas no período informado.
2. **Complementação:** coleta os dados complementares das atas e seus itens/resultados.
3. **Transformação:** estrutura os dados em DataFrames de atas, itens e resultados.
4. **Validação:** verifica identificadores, relacionamentos e campos obrigatórios; registra problemas em relatório.
5. **Carga:** persiste os dados no PostgreSQL, mantendo os registros brutos na staging e os dados estruturados nas tabelas normalizadas.

O diagrama está disponível em [`docs/diagrama_etl_pncp.svg`](docs/diagrama_etl_pncp.svg).

## 2. Tecnologias

- Python
- Apache Airflow 3.3.2
- Docker e Docker Compose
- PostgreSQL
- Pandas
- Requests
- Psycopg2

As dependências Python estão relacionadas em `requirements.txt`.

## 3. Estrutura do projeto

Estrutura lógica dos principais componentes:

```text
.
├── dags/
│   └── dag_pncp.py
├── pncp/
│   ├── __init__.py
│   ├── extracao.py
│   ├── exportacao.py
│   ├── transformacao.py
│   ├── validacao.py
│   └── carga.py
├── sql/
│   └── criar_tabelas.sql
├── dados/
│   ├── dados_pncp_20261001_20261028.json
│   └── relatorio_qualidade_pncp.csv
├── docs/
│   └── diagrama_etl_pncp.svg
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
└── .env
```

Os arquivos de dados e relatórios são gerados durante o processamento. A presença de arquivos de amostra pode variar conforme a versão entregue do projeto.

## 4. Pré-requisitos

- Docker Desktop instalado e em execução.
- Docker Compose disponível pelo comando `docker compose`.
- Git (opcional, para clonar o repositório).
- Acesso à internet para consultar a API pública do PNCP.

## 5. Configuração do ambiente

1. Obtenha o projeto e abra o terminal na pasta raiz.
2. Crie o arquivo `.env` a partir de um modelo `.env.example`, caso esse modelo esteja disponível. Se não houver modelo, crie `.env` com as variáveis utilizadas pelo `docker-compose.yaml` e pelo código.
3. Preencha os valores de ambiente necessários. Entre as variáveis utilizadas pelo projeto estão:

```dotenv
AIRFLOW_UID=
FERNET_KEY=

POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
```

`POSTGRES_*` representa a conexão do pipeline com o banco PostgreSQL de destino. Configure `POSTGRES_HOST` conforme a topologia do Docker Compose: dentro da rede Docker, utilize o nome do serviço/container do banco de destino, e não `localhost`.

**Segurança:** não coloque senhas ou chaves reais no Git. O arquivo `.env` deve permanecer ignorado pelo `.gitignore`. Compartilhe apenas um `.env.example` sem valores secretos.

## 6. Subir o ambiente Airflow

Na pasta raiz do projeto, execute:

```bash
docker compose config --quiet
docker compose build
docker compose up -d
```

Verifique os serviços:

```bash
docker compose ps
```

Consulte os logs em caso de problema:

```bash
docker compose logs --tail=100
```

A interface web do Airflow fica disponível em:

```text
http://127.0.0.1:8080
```

Use as credenciais configuradas no ambiente/arquivo Compose. Não inclua credenciais reais nesta documentação.

Para parar os serviços sem remover os volumes:

```bash
docker compose stop
```

Para iniciar novamente:

```bash
docker compose start
```

## 7. Executar a DAG

1. Acesse `http://127.0.0.1:8080`.
2. Localize a DAG **`etl_pncp`**.
3. Habilite a DAG, se necessário.
4. Acione **Trigger DAG** pela interface.
5. Informe os parâmetros `data_inicial` e `data_final`, quando desejar alterar o período de consulta.

As datas devem seguir o formato `AAAAMMDD`. A configuração padrão registrada na DAG utiliza `20261001` a `20261028`. A DAG está configurada para execução manual (`schedule=None`) e sem processamento retroativo (`catchup=False`).

A sequência de tarefas implementada é:

```text
extrair_atas_task
    → extrair_complementos
    → transformar_dados
    → validar_dados
    → carregar_postgresql
```

Acompanhe o estado e os logs de cada tarefa na visualização Graph/Grid da execução.

## 8. Persistência dos dados

O pipeline utiliza uma camada de staging e tabelas normalizadas.

- **`stg_pncp_registros`:** armazena o JSON original da ata, associado ao identificador da coleta (`coleta_id`) e ao número de controle da ata. Em uma nova coleta, um novo `coleta_id` preserva o histórico. Em conflito dentro da mesma coleta e para a mesma ata, o registro correspondente é atualizado.
- **`pncp_atas`:** armazena os dados estruturados das atas.
- **`pncp_itens`:** armazena os itens vinculados às atas.
- **`pncp_resultados`:** armazena os resultados vinculados aos itens.

A carga das tabelas normalizadas utiliza a estratégia de atualização/inserção implementada no módulo `pncp/carga.py`, permitindo reprocessamento sem duplicar registros pela chave de negócio definida no código.

O script de criação da estrutura está previsto em `sql/criar_tabelas.sql`. Execute-o no banco de destino antes da primeira carga, caso as tabelas ainda não tenham sido criadas. Confira os nomes e comandos do script versionado antes de executá-lo em um banco que já contenha dados.

## 9. Arquivos gerados e validação

Entre os arquivos utilizados/gerados pelo fluxo estão:

- `dados/atas_extraidas.json`: resultado da extração inicial.
- `dados/dados_pncp_20261001_20261028.json`: amostra de dados coletados no período de referência.
- `dados/relatorio_qualidade_pncp.csv`: relatório consolidado de qualidade.

Os relatórios específicos de registros inválidos podem ser gravados em `dados/relatorios/`, conforme as funções do módulo de validação.

### Como validar a execução

1. Na interface do Airflow, confirme que todas as tarefas da execução terminaram com estado **success**.
2. Consulte os logs das tarefas de validação e carga e verifique se não houve exceções.
3. No PostgreSQL, confira a existência das tabelas e a quantidade de registros:

```sql
SELECT COUNT(*) FROM stg_pncp_registros;
SELECT COUNT(*) FROM pncp_atas;
SELECT COUNT(*) FROM pncp_itens;
SELECT COUNT(*) FROM pncp_resultados;
```

4. Abra `dados/relatorio_qualidade_pncp.csv` e os relatórios de inválidos, quando gerados.
5. Verifique se os relacionamentos entre atas, itens e resultados estão íntegros.

### Resultado de referência registrado

Na amostra de referência foram estruturados:

- 10 atas;
- 358 itens;
- 296 resultados.

Em uma execução registrada em 02/11/2026, a etapa de extração processou 10 atas, sem falhas de extração. Os quantitativos podem variar conforme o período consultado e os dados publicados pelo PNCP.

## 10. API pública utilizada

A extração consulta a API pública de atas do PNCP:

`https://pncp.gov.br/api/consulta/v1/atas`

A consulta utiliza, entre outros, os parâmetros `dataInicial`, `dataFinal`, `pagina` e `tamanhoPagina`. As datas são enviadas no formato `AAAAMMDD`.

## 11. Observações

- A coleta é feita pela API pública do PNCP; o projeto não depende de raspagem de páginas HTML.
- O período de consulta é parametrizável na execução da DAG.
- A staging preserva o JSON de origem e o histórico por coleta.
- Os dados inválidos devem ser registrados em relatórios para permitir análise, em vez de serem descartados silenciosamente.
- Ajuste os nomes de serviços/hosts e credenciais de acordo com o `docker-compose.yaml` e o ambiente local.


## 🎥 Demonstração do Projeto

Para apresentar o funcionamento do pipeline ETL desenvolvido para o PNCP, disponibilizei um vídeo demonstrativo com a execução e explicação das principais etapas do projeto.

A demonstração contempla:

* Extração de dados pela API pública do PNCP.
* Transformação e estruturação dos dados com Python e Pandas.
* Validação da qualidade dos dados e identificação de inconsistências.
* Persistência dos dados no PostgreSQL.
* Orquestração e execução do pipeline com Apache Airflow.
* Execução em ambiente Docker.

▶️ **[ASSISTIR À DEMONSTRAÇÃO DO PROJETO NO YOUTUBE](https://youtu.be/Gxc_aCSWMHI)**
