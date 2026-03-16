"""
Airflow AI SDK example that combines structured extraction and LLM branching.
"""

import ast
import json
import os
import re
from typing import Any, Literal

import pendulum
from pydantic import BaseModel, Field

try:
    from airflow.sdk import dag, task
except ImportError:
    from airflow.decorators import dag, task

from airflow.models.dagrun import DagRun

DEFAULT_MODEL = os.getenv("LLM_MODEL", "ollama:llama3.2")


class TicketAssessment(BaseModel):
    summary: str = Field(description="A concise summary of the incident.")
    priority: Literal["p0", "p1", "p2", "p3"]
    owning_team: Literal["platform", "spark", "lineage"]
    reply: str = Field(description="A short customer-facing reply.")


@task.llm(
    model=DEFAULT_MODEL,
    output_type=str,
    system_prompt="""
    You are an incident triage assistant for a data platform team.

    Read the ticket and return only a JSON object with these keys:
    - summary
    - priority
    - owning_team
    - reply

    Allowed values:
    - priority: p0, p1, p2, p3
    - owning_team: platform, spark, lineage

    Do not wrap the JSON in markdown.
    Do not return a tool call envelope.
    """,
)
def generate_ticket_assessment(dag_run: DagRun) -> str:
    return dag_run.conf.get(
        "ticket",
        "The nightly Spark transform failed and no curated orders dataset was produced.",
    )


@task
def parse_ticket_assessment(raw_assessment: str) -> dict[str, Any]:
    cleaned = raw_assessment.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        payload = ast.literal_eval(cleaned)

    if isinstance(payload, dict) and "parameters" in payload and isinstance(payload["parameters"], dict):
        payload = payload["parameters"]

    return TicketAssessment.model_validate(payload).model_dump()


@task.branch
def route_ticket(assessment: dict[str, Any]) -> str:
    route_map = {
        "platform": "handle_platform_ticket",
        "spark": "handle_spark_ticket",
        "lineage": "handle_lineage_ticket",
    }
    return route_map[assessment["owning_team"]]


@task
def publish_reply(assessment: dict[str, Any]) -> None:
    print("Suggested reply")
    print(assessment["reply"])


@task
def handle_platform_ticket(assessment: dict[str, Any]) -> None:
    print(f"Platform team handling: {assessment['summary']}")


@task
def handle_spark_ticket(assessment: dict[str, Any]) -> None:
    print(f"Spark team handling: {assessment['summary']}")


@task
def handle_lineage_ticket(assessment: dict[str, Any]) -> None:
    print(f"Lineage team handling: {assessment['summary']}")


@dag(
    dag_id="ai_support_router",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    params={
        "ticket": "OpenLineage stopped updating after our latest Spark code change and the Airflow run needs help."
    },
    tags=["ai-sdk", "agentic", "triage", "ollama"],
)
def ai_support_router():
    assessment = parse_ticket_assessment(generate_ticket_assessment())
    publish_reply(assessment)
    router = route_ticket(assessment)
    platform_task = handle_platform_ticket(assessment)
    spark_task = handle_spark_ticket(assessment)
    lineage_task = handle_lineage_ticket(assessment)

    router >> [platform_task, spark_task, lineage_task]


ai_support_router()
