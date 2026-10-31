from datetime import datetime

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="etl_postgres_clickhouse",
    description="ETL incremental de vendas do PostgreSQL para o ClickHouse",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["ETL", "PostgreSQL", "ClickHouse"],
) as dag:

    executar_etl = BashOperator(
        task_id="executar_etl",
        bash_command=(
            "cd /opt/airflow/clickhouse_etl "
            "&& python -m scripts.executar_etl"
        ),
    )