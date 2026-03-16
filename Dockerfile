FROM apache/airflow:3.1.8-python3.12

ARG AIRFLOW_AI_SDK_REF=70ec7cb03d34cc010c6f7face39f80664691be9c
ARG AIRFLOW_CONSTRAINTS=https://raw.githubusercontent.com/apache/airflow/constraints-3.1.8/constraints-3.12.txt

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV SPARK_LOCAL_DIRS=/tmp/spark
ENV PYSPARK_PYTHON=python

COPY --chown=airflow:root requirements.txt /tmp/requirements.txt
COPY --chown=airflow:root requirements-airflow.txt /tmp/requirements-airflow.txt

USER airflow

RUN pip install --no-cache-dir --user --constraint "${AIRFLOW_CONSTRAINTS}" -r /tmp/requirements-airflow.txt \
    && pip install --no-cache-dir --user "apache-airflow==3.1.8" -r /tmp/requirements.txt \
    && rm /tmp/requirements-airflow.txt /tmp/requirements.txt
