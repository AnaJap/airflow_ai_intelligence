# Airflow 3 + `airflow-ai-sdk` Demo

This repository starts Apache Airflow 3.1.8 in Docker, installs Astronomer's [`airflow-ai-sdk`](https://github.com/astronomer/airflow-ai-sdk/tree/main), and ships a few runnable demo DAGs:

- `ai_support_router`: structured ticket triage with `@task.llm` and `@task.llm_branch`
- `ai_ops_agent`: an agentic helper with `@task.agent` and local tools
- `spark_ai_lineage_demo`: an AI-assisted Spark run that emits lineage to Marquez via OpenLineage

It is meant to be a practical local sandbox for Airflow-native AI tasks, not a production-ready deployment.

## What is included

- Airflow 3.1.8 split services: `api-server`, `scheduler`, `dag-processor`, and `triggerer`
- Postgres for Airflow metadata and Marquez metadata
- Marquez API and UI for browsing lineage
- A custom Airflow image with:
  - `airflow-ai-sdk` pinned to GitHub commit `70ec7cb03d34cc010c6f7face39f80664691be9c`
  - `pyspark==3.5.5`
  - `apache-airflow-providers-openlineage`
- A sample PySpark job that curates JSON orders into parquet and writes simple run metrics

## Prerequisites

- Docker Desktop running
- An OpenAI API key if you want the AI SDK tasks to execute

## Quick start

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Set `OPENAI_API_KEY` in `.env`.

3. Start the stack:

```bash
docker compose up --build
```

4. Open the local tools:

- Airflow UI: `http://localhost:8080`
- Marquez UI: `http://localhost:3000`
- Marquez API: `http://localhost:5000`

## Demo DAGs

### 1. `ai_support_router`

This DAG demonstrates the two most immediately useful SDK patterns:

- `@task.llm` to convert a raw incident into structured output
- `@task.llm_branch` to choose the next task id dynamically

Trigger it with:

```json
{
  "ticket": "Our Spark transformation completed but Marquez shows no fresh lineage for curated orders."
}
```

### 2. `ai_ops_agent`

This DAG uses `@task.agent` with local tools instead of internet search. It can inspect:

- the demo asset inventory
- a preview of the raw orders file
- the most recent Spark metrics file

Trigger it with:

```json
{
  "question": "Explain the stack, the data that Spark reads, and what I should inspect after a run."
}
```

### 3. `spark_ai_lineage_demo`

This DAG does three things:

1. asks an LLM for a short Spark pre-flight checklist
2. runs `spark-submit` locally inside the Airflow container
3. asks an agent to summarize the resulting metrics and curated output

The Spark command includes the OpenLineage listener and publishes to Marquez.

## Dependency note

The Docker build intentionally installs Airflow-managed packages with the official Airflow constraints first, then installs demo-specific packages like `pyspark==3.5.5` and `airflow-ai-sdk` in a second step. This avoids conflicts with the broader Airflow constraints bundle.

## Spark lineage notes

The Spark demo uses:

- `io.openlineage:openlineage-spark_2.12:1.45.0`
- `spark.extraListeners=io.openlineage.spark.agent.OpenLineageSparkListener`
- `spark.openlineage.transport.type=http`
- `spark.openlineage.transport.url=http://marquez:5000`

If your local Spark distribution expects a different Scala binary, update the artifact suffix in [`dags/spark_ai_lineage_demo.py`](dags/spark_ai_lineage_demo.py).

## Useful commands

Rebuild after dependency changes:

```bash
docker compose up --build
```

Stop everything:

```bash
docker compose down
```

Remove state and start clean:

```bash
docker compose down -v
```

## Sources used

- Airflow AI SDK repo: https://github.com/astronomer/airflow-ai-sdk/tree/main
- Airflow AI SDK usage/examples in the repo docs and example DAGs
- Airflow 3 Docker Compose reference: https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html
- OpenLineage Spark installation/configuration docs: https://openlineage.io/docs/integrations/spark/installation and https://openlineage.io/docs/integrations/spark/configuration/usage
