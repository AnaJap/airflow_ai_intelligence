"""
Simple PySpark transformation used by the Airflow demo DAG.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

ROOT = Path("/opt/airflow/include")
INPUT_PATH = ROOT / "raw" / "orders.json"
OUTPUT_PATH = ROOT / "processed" / "orders_curated"
METRICS_PATH = ROOT / "processed" / "orders_metrics.json"


def main() -> None:
    spark = SparkSession.builder.appName("orders-curation-demo").getOrCreate()

    df = spark.read.json(str(INPUT_PATH))

    curated = (
        df.filter(F.col("customer_id").isNotNull())
        .withColumn("order_ts", F.to_timestamp("order_ts"))
        .withColumn("status", F.upper(F.col("status")))
        .withColumn("gross_revenue", F.round(F.col("quantity") * F.col("unit_price"), 2))
        .withColumn("is_high_value", F.col("quantity") * F.col("unit_price") >= F.lit(100))
        .select(
            "order_id",
            "customer_id",
            "order_ts",
            "product",
            "status",
            "quantity",
            "unit_price",
            "gross_revenue",
            "is_high_value",
        )
    )

    if OUTPUT_PATH.exists():
        shutil.rmtree(OUTPUT_PATH)

    curated.write.mode("overwrite").parquet(str(OUTPUT_PATH))

    metrics = {
        "input_rows": df.count(),
        "curated_rows": curated.count(),
        "high_value_orders": curated.filter(F.col("is_high_value")).count(),
        "total_revenue": curated.agg(F.sum("gross_revenue").alias("revenue")).collect()[0]["revenue"],
        "output_path": str(OUTPUT_PATH),
    }

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    spark.stop()


if __name__ == "__main__":
    main()

