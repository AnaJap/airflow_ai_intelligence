"""
Airflow AI SDK example that uses @task.agent with local tools to answer ops questions.
"""

import os
from pathlib import Path

import pendulum
from pydantic_ai import Agent

try:
    from airflow.sdk import dag, task
except ImportError:
    from airflow.decorators import dag, task

from airflow.models.dagrun import DagRun

ROOT = Path("/opt/airflow")
RAW_DATA = ROOT / "include" / "raw" / "orders.json"
METRICS_FILE = ROOT / "include" / "processed" / "orders_metrics.json"
DEFAULT_MODEL = os.getenv("LLM_MODEL", "ollama:llama3.2")


def read_raw_orders_preview() -> str:
    return RAW_DATA.read_text(encoding="utf-8")[:1200]


def describe_demo_assets() -> str:
    return """
    Available demo assets:
    - Airflow UI: http://localhost:8080
    - Marquez API: http://localhost:5000
    - Marquez UI: http://localhost:3000
    - Spark input file: /opt/airflow/include/raw/orders.json
    - Spark output folder: /opt/airflow/include/processed/orders_curated
    - Spark metrics file: /opt/airflow/include/processed/orders_metrics.json
    """.strip()


def read_latest_metrics() -> str:
    if not METRICS_FILE.exists():
        return "No Spark metrics have been generated yet."
    return METRICS_FILE.read_text(encoding="utf-8")


ops_agent = Agent(
    DEFAULT_MODEL,
    system_prompt="""
    You are an Airflow operations copilot for a local demo environment.
    Use the available tools before answering.
    Ground your answer in the tool output and keep recommendations practical.
    """,
    tools=[read_raw_orders_preview, describe_demo_assets, read_latest_metrics],
)


@task.agent(agent=ops_agent)
def answer_ops_question(dag_run: DagRun) -> str:
    return dag_run.conf.get(
        "question",
        "What is this demo stack made of, what data does the Spark job read, and what should I inspect after a run?",
    )


@task
def print_answer(answer: str) -> None:
    print(answer)


@dag(
    dag_id="ai_ops_agent",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    params={
        "question": "Explain the local stack, the raw dataset, and the first lineage checks to make in Marquez."
    },
    tags=["ai-sdk", "agent", "ollama"],
)
def ai_ops_agent():
    print_answer(answer_ops_question())


ai_ops_agent()
