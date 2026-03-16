"""
Sample HITL DAG for backfill approval workflow.
"""

import pendulum

try:
    from airflow.sdk import Param, dag, task
except ImportError:
    from airflow.decorators import dag, task
    from airflow.models.param import Param

from airflow.providers.standard.operators.hitl import ApprovalOperator, HITLEntryOperator


@task
def propose_backfill() -> dict[str, object]:
    return {
        "dataset": "orders_gold",
        "date_range": "2025-01-01 to 2025-02-14",
        "estimated_partitions": 45,
        "estimated_compute_hours": 6,
        "downstream_impact": ["finance_daily_kpis", "exec_dashboard", "forecast_features"],
    }


@task
def execute_backfill() -> None:
    print("Backfill approved. Launching controlled backfill execution.")


@dag(
    dag_id="hitl_backfill_approval",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=["hitl", "backfill"],
)
def hitl_backfill_approval():
    proposal = propose_backfill()

    capture_backfill_controls = HITLEntryOperator(
        task_id="capture_backfill_controls",
        subject="Provide run controls for the proposed backfill",
        body="""
        Dataset: {{ ti.xcom_pull(task_ids='propose_backfill')['dataset'] }}
        Date range: {{ ti.xcom_pull(task_ids='propose_backfill')['date_range'] }}
        Estimated partitions: {{ ti.xcom_pull(task_ids='propose_backfill')['estimated_partitions'] }}
        Estimated compute hours: {{ ti.xcom_pull(task_ids='propose_backfill')['estimated_compute_hours'] }}
        Downstream impact: {{ ti.xcom_pull(task_ids='propose_backfill')['downstream_impact'] }}
        """,
        params={
            "justification": Param("", type="string"),
            "concurrency_cap": Param(4, type="integer"),
            "batch_strategy": Param("daily", enum=["daily", "weekly"]),
        },
    )

    approve_backfill = ApprovalOperator(
        task_id="approve_backfill",
        subject="Approve this backfill plan?",
        body="""
        Justification: {{ ti.xcom_pull(task_ids='capture_backfill_controls')['params_input']['justification'] }}
        Concurrency cap: {{ ti.xcom_pull(task_ids='capture_backfill_controls')['params_input']['concurrency_cap'] }}
        Batch strategy: {{ ti.xcom_pull(task_ids='capture_backfill_controls')['params_input']['batch_strategy'] }}
        """,
        defaults="Reject",
    )

    proposal >> capture_backfill_controls >> approve_backfill >> execute_backfill()


hitl_backfill_approval()

