"""
Spark + Airflow AI SDK example with Marquez/OpenLineage integration.
"""

import os
from pathlib import Path

import pendulum
from pydantic_ai import Agent

try:
    from airflow.sdk import dag, task
except ImportError:
    from airflow.decorators import dag, task

from airflow.datasets import Dataset
from airflow.operators.bash import BashOperator

ROOT = Path("/opt/airflow")
RAW_ORDERS_PATH = ROOT / "include" / "raw" / "orders.json"
CURATED_ORDERS_PATH = ROOT / "include" / "processed" / "orders_curated"
METRICS_PATH = ROOT / "include" / "processed" / "orders_metrics.json"
DEFAULT_MODEL = os.getenv("LLM_MODEL", "ollama:llama3.2")

RAW_ORDERS = Dataset("file:///opt/airflow/include/raw/orders.json")
CURATED_ORDERS = Dataset("file:///opt/airflow/include/processed/orders_curated")


@task.llm(
    model=DEFAULT_MODEL,
    output_type=str,
    system_prompt="""
    You are preparing a Spark transformation run.
    Provide a compact pre-flight checklist with data quality checks and lineage expectations.
    """,
)
def create_preflight_note() -> str:
    return RAW_ORDERS_PATH.read_text(encoding="utf-8")[:1600]


def read_metrics() -> str:
    if not METRICS_PATH.exists():
        return "Metrics file not found. The Spark task may not have run yet."
    return METRICS_PATH.read_text(encoding="utf-8")


def preview_curated_data() -> str:
    if not CURATED_ORDERS_PATH.exists():
        return "Curated output folder not found yet."
    files = sorted(CURATED_ORDERS_PATH.glob("part-*.parquet"))
    if not files:
        return "Curated output folder exists, but no parquet parts were found."
    return f"Curated parquet parts: {[file.name for file in files[:5]]}"


run_summary_agent = Agent(
    DEFAULT_MODEL,
    system_prompt="""
    You are summarizing the outcome of a local Spark data pipeline run.
    Use the available tools and mention both data quality and lineage visibility.
    """,
    tools=[read_metrics, preview_curated_data],
)


@task.agent(agent=run_summary_agent)
def summarize_run(preflight_note: str) -> str:
    return f"Pre-flight note for context:\n{preflight_note}"


@task
def print_summary(summary: str) -> None:
    print(summary)


@dag(
    dag_id="spark_ai_lineage_demo",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=["spark", "ai-sdk", "openlineage", "ollama"],
)
def spark_ai_lineage_demo():
    preflight_note = create_preflight_note()

    spark_job = BashOperator(
        task_id="run_spark_transform",
        bash_command="""
        set -euo pipefail
        spark-submit \
          --master local[*] \
          --packages io.openlineage:openlineage-spark_2.12:1.45.0 \
          --conf spark.extraListeners=io.openlineage.spark.agent.OpenLineageSparkListener \
          --conf spark.openlineage.transport.type=http \
          --conf spark.openlineage.transport.url=http://marquez:5000 \
          --conf spark.openlineage.namespace=airflow-intelligence-demo \
          /opt/airflow/jobs/transform_orders.py
        """,
        inlets=[RAW_ORDERS],
        outlets=[CURATED_ORDERS],
    )

    summary = summarize_run(preflight_note)
    print_task = print_summary(summary)

    preflight_note >> spark_job
    spark_job >> summary
    summary >> print_task


spark_ai_lineage_demo()
