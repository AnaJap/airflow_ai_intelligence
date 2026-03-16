# Airflow 3 + `airflow-ai-sdk` Demo

This repository starts Apache Airflow 3.1.8 in Docker, installs Astronomer's [`airflow-ai-sdk`](https://github.com/astronomer/airflow-ai-sdk/tree/main), and ships a few runnable demo DAGs.

By default, the AI tasks run against a local Ollama model so you can use the project without OpenAI API credits. The OpenAI-based setup still remains possible by changing environment variables.

Included demo DAGs:

- `ai_support_router`: structured ticket triage with `@task.llm` plus deterministic Python routing
- `ai_ops_agent`: an agentic helper with `@task.agent` and local tools
- `spark_ai_lineage_demo`: an AI-assisted Spark run that emits lineage to Marquez via OpenLineage
- `hitl_data_quality_exception_review`: branch-based human review of failed quality checks
- `hitl_schema_change_approval`: human approval gate for detected schema diffs
- `hitl_backfill_approval`: human approval workflow for controlled backfills

It is meant to be a practical local sandbox for Airflow-native AI tasks, not a production-ready deployment.

## What is included

- Airflow 3.1.8 split services: `api-server`, `scheduler`, `dag-processor`, and `triggerer`
- Ollama for local LLM inference, plus an automatic model pull step
- Postgres for Airflow metadata and Marquez metadata
- Marquez API and UI for browsing lineage
- A custom Airflow image with:
  - `airflow-ai-sdk` pinned to GitHub commit `70ec7cb03d34cc010c6f7face39f80664691be9c`
  - `pyspark==3.5.5`
  - `apache-airflow-providers-openlineage`
- A sample PySpark job that curates JSON orders into parquet and writes simple run metrics

## Prerequisites

- Docker Desktop running

You do not need an OpenAI API key for the default setup.

## Quick start

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Start the stack:

```bash
docker compose up --build
```

The first startup pulls the default Ollama model, so it can take a few minutes.

3. Open the local tools:

- Airflow UI: `http://localhost:8080`
- Marquez UI: `http://localhost:3000`
- Marquez API: `http://localhost:5000`
- Ollama API: `http://localhost:11434`

## Default local AI mode

The repo defaults to:

- `LLM_MODEL=ollama:llama3.2`
- `OLLAMA_MODEL_NAME=llama3.2`
- `OLLAMA_BASE_URL=http://ollama:11434/v1`

Those settings are passed into the Airflow containers and used by all example DAGs.

If you want a stronger local model, change both `LLM_MODEL` and `OLLAMA_MODEL_NAME`, for example:

```env
LLM_MODEL=ollama:gpt-oss:20b
OLLAMA_MODEL_NAME=gpt-oss:20b
```

Then rerun:

```bash
docker compose up --build
```

Smaller local models are convenient, but they may be less reliable for strict branching or structured outputs than larger local models or hosted APIs.

## Optional OpenAI mode

If you want to use OpenAI instead of Ollama, update `.env` like this:

```env
OPENAI_API_KEY=your-key
LLM_MODEL=openai:gpt-4o-mini
```

Then restart the stack. The rest of the repo stays the same.

## Demo DAGs

### 1. `ai_support_router`

This DAG demonstrates a local-model-friendly AI triage flow:

- `@task.llm` to convert a raw incident into structured JSON
- Python-side validation and routing so Ollama-sized models are more reliable locally

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

### 4. HITL samples

The repo also includes three Human-in-the-Loop samples based on Airflow 3 HITL operators:

- `hitl_data_quality_exception_review`
  Uses `HITLEntryOperator` and `HITLBranchOperator` so a human can capture incident context and choose whether to quarantine, release with warning, or rerun upstream jobs.

- `hitl_schema_change_approval`
  Uses `HITLEntryOperator` plus `ApprovalOperator` to review schema diffs and gate downstream rollout.

- `hitl_backfill_approval`
  Uses `HITLEntryOperator` plus `ApprovalOperator` to capture backfill run controls and require approval before execution.

In Airflow UI, open the HITL task instance and use the Required Actions panel to respond.

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
