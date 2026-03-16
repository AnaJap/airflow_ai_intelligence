"""
Sample HITL DAG for schema change approval.
"""

import pendulum

try:
    from airflow.sdk import Param, dag, task
except ImportError:
    from airflow.decorators import dag, task
    from airflow.models.param import Param

from airflow.providers.standard.operators.hitl import ApprovalOperator, HITLEntryOperator


@task
def detect_schema_diff() -> dict[str, object]:
    return {
        "dataset": "orders_silver -> orders_gold",
        "new_columns": ["sales_channel", "customer_region"],
        "removed_columns": [],
        "type_changes": {"order_ts": "string -> timestamp"},
        "breaking_change": False,
    }


@task
def apply_schema_change() -> None:
    print("Schema migration approved and downstream models can be updated.")


@dag(
    dag_id="hitl_schema_change_approval",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=["hitl", "schema"],
)
def hitl_schema_change_approval():
    schema_diff = detect_schema_diff()

    capture_rollout_context = HITLEntryOperator(
        task_id="capture_rollout_context",
        subject="Enter rollout context for the detected schema change",
        body="""
        Dataset path: {{ ti.xcom_pull(task_ids='detect_schema_diff')['dataset'] }}
        New columns: {{ ti.xcom_pull(task_ids='detect_schema_diff')['new_columns'] }}
        Removed columns: {{ ti.xcom_pull(task_ids='detect_schema_diff')['removed_columns'] }}
        Type changes: {{ ti.xcom_pull(task_ids='detect_schema_diff')['type_changes'] }}
        Breaking change: {{ ti.xcom_pull(task_ids='detect_schema_diff')['breaking_change'] }}
        """,
        params={
            "change_ticket": Param("", type="string"),
            "planned_window": Param("", type="string"),
            "rollout_notes": Param("", type="string"),
        },
    )

    approve_schema_change = ApprovalOperator(
        task_id="approve_schema_change",
        subject="Approve publishing this schema change to downstream consumers?",
        body="""
        Change ticket: {{ ti.xcom_pull(task_ids='capture_rollout_context')['params_input']['change_ticket'] }}
        Planned window: {{ ti.xcom_pull(task_ids='capture_rollout_context')['params_input']['planned_window'] }}
        Rollout notes: {{ ti.xcom_pull(task_ids='capture_rollout_context')['params_input']['rollout_notes'] }}
        """,
        defaults="Reject",
    )

    schema_diff >> capture_rollout_context >> approve_schema_change >> apply_schema_change()


hitl_schema_change_approval()

