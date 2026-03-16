"""
Airflow AI SDK example that combines structured extraction and LLM branching.
"""

from typing import Literal

import pendulum
from pydantic import BaseModel, Field

try:
    from airflow.sdk import dag, task
except ImportError:
    from airflow.decorators import dag, task

from airflow.models.dagrun import DagRun


class TicketAssessment(BaseModel):
    summary: str = Field(description="A concise summary of the incident.")
    priority: Literal["p0", "p1", "p2", "p3"]
    owning_team: Literal["platform", "spark", "lineage"]
    reply: str = Field(description="A short customer-facing reply.")


@task.llm(
    model="gpt-4o-mini",
    output_type=TicketAssessment,
    system_prompt="""
    You are an incident triage assistant for a data platform team.

    Read the ticket and return:
    - summary: short factual summary
    - priority: p0, p1, p2, or p3
    - owning_team: platform, spark, or lineage
    - reply: a short empathetic acknowledgement with the next step
    """,
)
def assess_ticket(dag_run: DagRun) -> str:
    return dag_run.conf.get(
        "ticket",
        "The nightly Spark transform failed and no curated orders dataset was produced.",
    )


@task.llm_branch(
    model="gpt-4o-mini",
    system_prompt="""
    Choose exactly one downstream task id based on the owning team in the payload.

    Return only one of:
    - handle_platform_ticket
    - handle_spark_ticket
    - handle_lineage_ticket
    """,
)
def route_ticket(assessment: TicketAssessment) -> str:
    return assessment.model_dump_json(indent=2)


@task
def publish_reply(assessment: TicketAssessment) -> None:
    print("Suggested reply")
    print(assessment.reply)


@task
def handle_platform_ticket(assessment: TicketAssessment) -> None:
    print(f"Platform team handling: {assessment.summary}")


@task
def handle_spark_ticket(assessment: TicketAssessment) -> None:
    print(f"Spark team handling: {assessment.summary}")


@task
def handle_lineage_ticket(assessment: TicketAssessment) -> None:
    print(f"Lineage team handling: {assessment.summary}")


@dag(
    dag_id="ai_support_router",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    params={
        "ticket": "OpenLineage stopped updating after our latest Spark code change and the Airflow run needs help."
    },
    tags=["ai-sdk", "agentic", "triage"],
)
def ai_support_router():
    assessment = assess_ticket()
    publish_reply(assessment)
    router = route_ticket(assessment)
    platform_task = handle_platform_ticket(assessment)
    spark_task = handle_spark_ticket(assessment)
    lineage_task = handle_lineage_ticket(assessment)

    router >> [platform_task, spark_task, lineage_task]


ai_support_router()
