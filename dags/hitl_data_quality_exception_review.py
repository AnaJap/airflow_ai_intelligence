"""
Sample HITL DAG for data quality exception review.
"""

import pendulum

try:
    from airflow.sdk import Param, dag, task
except ImportError:
    from airflow.decorators import dag, task
    from airflow.models.param import Param

from airflow.providers.standard.operators.hitl import HITLBranchOperator, HITLEntryOperator


@task
def profile_quality_issue() -> dict[str, object]:
    return {
        "dataset": "customer_orders_curated",
        "failed_checks": [
            "null_customer_id_rate > 0.5%",
            "duplicate_order_id_count > 0",
            "revenue_delta_vs_yesterday > 12%",
        ],
        "affected_rows": 1842,
        "recommended_action": "quarantine_batch",
    }


@task
def quarantine_batch() -> None:
    print("Batch quarantined for deeper investigation.")


@task
def release_with_warning() -> None:
    print("Batch released with a warning and incident follow-up.")


@task
def rerun_upstream() -> None:
    print("Upstream jobs flagged for rerun before another quality pass.")


@dag(
    dag_id="hitl_data_quality_exception_review",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=["hitl", "data-quality"],
)
def hitl_data_quality_exception_review():
    quality_report = profile_quality_issue()

    capture_review_input = HITLEntryOperator(
        task_id="capture_review_input",
        subject="Review data quality exceptions for customer_orders_curated",
        body="""
        Dataset: {{ ti.xcom_pull(task_ids='profile_quality_issue')['dataset'] }}

        Failed checks:
        {{ ti.xcom_pull(task_ids='profile_quality_issue')['failed_checks'] }}

        Affected rows:
        {{ ti.xcom_pull(task_ids='profile_quality_issue')['affected_rows'] }}

        Recommended action:
        {{ ti.xcom_pull(task_ids='profile_quality_issue')['recommended_action'] }}
        """,
        params={
            "incident_ticket": Param("", type="string"),
            "reviewer_notes": Param("", type="string"),
        },
    )

    choose_quality_disposition = HITLBranchOperator(
        task_id="choose_quality_disposition",
        subject="Choose the disposition for this failed quality batch",
        options=["quarantine_batch", "release_with_warning", "rerun_upstream"],
        body="""
        Ticket: {{ ti.xcom_pull(task_ids='capture_review_input')['params_input']['incident_ticket'] }}
        Reviewer notes: {{ ti.xcom_pull(task_ids='capture_review_input')['params_input']['reviewer_notes'] }}
        Recommended action: {{ ti.xcom_pull(task_ids='profile_quality_issue')['recommended_action'] }}
        """,
    )

    quality_report >> capture_review_input >> choose_quality_disposition
    choose_quality_disposition >> [quarantine_batch(), release_with_warning(), rerun_upstream()]


hitl_data_quality_exception_review()

