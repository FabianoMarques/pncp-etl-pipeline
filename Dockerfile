FROM apache/airflow:3.3.2

COPY --chown=airflow:root requirements.txt /tmp/etl-requirements.txt

RUN pip install --no-cache-dir -r /tmp/etl-requirements.txt
