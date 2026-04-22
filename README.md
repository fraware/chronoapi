<div align="center">

# ChronoAPI

**Forecast multivariate time series in production** using IBM Granite **Tiny Time Mixer (TTM)** models.

FastAPI · OpenAPI · Optional Kafka · Prometheus · Docker-ready

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-4b5563?style=flat-square)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fastral-sh%2Fruff%2Fmain%2Fassets%2Fbadge%2Fv2.json&style=flat-square)](https://github.com/astral-sh/ruff)

[Source](https://github.com/fraware/chronoapi) · [Quick start](#quick-start) · [API reference](#rest-api-at-a-glance) · [Docker](#deployment) · [Model card](MODEL-DESCRIPTION.md)

</div>

---

ChronoAPI is a small, opinionated service layer around [`granite-tsfm`](https://github.com/ibm-granite/granite-tsfm): it loads a TTM checkpoint from Hugging Face, exposes **HTTP** and optionally **Kafka** for the same forecast contract, and ships **metrics** and **structured logs** so you can run it behind a gateway or inside a data pipeline without writing glue code.

**Why this stack?** TTM models are compact enough for CPU-friendly inference; FastAPI gives you typed request bodies and live docs; Prometheus and optional JSON logging fit standard observability stacks.

---

## Features

| Area | What you get |
|------|----------------|
| **Inference** | `POST /forecast` with configurable `context_length` and `forecast_length`. |
| **Fine-tuning** | `POST /finetune` synchronously, or async jobs with `FINETUNE_ASYNC` and status polling. |
| **Streaming** | Optional Kafka consumer: same JSON as `/forecast` in, forecast JSON out. |
| **Operations** | `GET /metrics` (Prometheus), `/health/live` and `/health/ready`, optional JSON logs. |
| **Hardening** | Optional `API_KEY` + `X-API-Key`, `X-Request-ID` on every response. |

Open the interactive contract anytime at **`/docs`** (Swagger) or **`/redoc`** once the server is up.

---

## Quick start

**Prerequisites:** Python **3.11+** (3.12 matches Docker). First inference run needs Hugging Face access unless you use a warm `HF_HOME` cache or `SKIP_MODEL_LOAD=1` for tests.

```bash
git clone https://github.com/fraware/chronoapi.git
cd chronoapi
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000/docs**. Kafka stays **off** until you set `KAFKA_ENABLED=true` and point brokers at `KAFKA_BOOTSTRAP_SERVERS`.

**Developers** (lint, tests, types):

```bash
pip install -e ".[dev]"
```

**Distributed tracing** (optional):

```bash
pip install -e ".[otel]"
```

---

## Project layout

| Location | Responsibility |
|----------|------------------|
| [`app/main.py`](app/main.py) | ASGI app entry. |
| [`app/api/factory.py`](app/api/factory.py) | Lifespan, middleware, routing assembly. |
| [`app/api/routes/`](app/api/routes/) | HTTP handlers: health, forecast, finetune, metrics. |
| [`app/services/`](app/services/) | Forecasting, training, Kafka loop, async job registry. |
| [`app/schemas/`](app/schemas/) | Pydantic models for JSON bodies. |
| [`app/model.py`](app/model.py) | Loads TTM; dummy model when `SKIP_MODEL_LOAD=1`. |
| [`app/config.py`](app/config.py) | Environment-driven settings. |
| [`tests/`](tests/) | Pytest (no model download required). |
| [`docker-compose.yaml`](docker-compose.yaml) · [`Dockerfile`](Dockerfile) | Full stack and production image. |
| [`MODEL-DESCRIPTION.md`](MODEL-DESCRIPTION.md) | TTM-R2 model card + how ChronoAPI uses it. |

---

## Configuration

Settings load from the environment and optional **`.env`** in the project root (`pydantic-settings`).

<details>
<summary><strong>Environment variables</strong> (click to expand)</summary>

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOG_LEVEL` | `INFO` | Logging verbosity. |
| `JSON_LOGS` | `false` | Emit JSON lines to stdout. |
| `WORKER_COUNT` | `4` | Gunicorn workers in the container entrypoint. |
| `KAFKA_ENABLED` | `false` | Start the forecast consumer at startup. |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Broker addresses. |
| `KAFKA_INPUT_TOPIC` | `forecast_requests` | Request topic. |
| `KAFKA_OUTPUT_TOPIC` | `forecast_responses` | Response topic. |
| `SKIP_MODEL_LOAD` | `false` | Skip HF download; use a dummy model. |
| `API_KEY` | — | If set, require matching `X-API-Key` on protected routes. |
| `FINETUNE_ASYNC` | `false` | Return **202** + `job_id` from `POST /finetune`; poll `GET /finetune/jobs/{job_id}`. |

</details>

**Headers**

- **`X-Request-ID`** — Optional; server generates one if missing and returns it on the response.
- **`X-API-Key`** — Required when `API_KEY` is set, except on `/health*`, `/metrics`, `/docs`, `/redoc`, `/openapi.json`.

**Health**

| Endpoint | Role |
|----------|------|
| `GET /health` | Legacy OK. |
| `GET /health/live` | Liveness. |
| `GET /health/ready` | Readiness (model attached). |

**Lockfiles for production:** Prefer a committed lockfile from [pip-tools](https://github.com/jazzband/pip-tools) or [uv](https://github.com/astral-sh/uv). [`requirements.txt`](requirements.txt) stays on compatible ranges for flexibility.

---

## REST API at a glance

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/forecast` | Body: [`ForecastRequest`](app/schemas/requests.py). You need enough rows to satisfy `context_length` (default 512). |
| `POST` | `/finetune` | Body: `FineTuneRequest`; at least **three** rows in `data`. |
| `GET` | `/finetune/jobs/{job_id}` | Async job status when `FINETUNE_ASYNC=true`. |
| `GET` | `/metrics` | Prometheus text format. |

Validation issues and expected rule violations (e.g. too few history rows) surface as **422** where applicable.

---

## Usage examples

### Liveness

```bash
curl -s http://localhost:8000/health/live
```

```json
{"status":"ok"}
```

### Forecast payload shape

Each row needs a **`date`** (datetime string) plus **`HUFL`**, **`HULL`**, **`MUFL`**, **`MULL`**, **`LUFL`**, **`LULL`**, **`OT`** (ETTh-style defaults). Below is a **structural** sample only—extend `data` until `len(data) >= context_length` before calling the API.

```json
{
  "data": [
    {
      "date": "2023-01-01 00:00",
      "HUFL": 1.2,
      "HULL": 0.5,
      "MUFL": 1.0,
      "MULL": 0.8,
      "LUFL": 1.1,
      "LULL": 0.7,
      "OT": 1.3
    },
    {
      "date": "2023-01-01 00:10",
      "HUFL": 1.3,
      "HULL": 0.6,
      "MUFL": 1.1,
      "MULL": 0.9,
      "LUFL": 1.2,
      "LULL": 0.8,
      "OT": 1.4
    }
  ],
  "context_length": 512,
  "forecast_length": 96,
  "request_id": "test123"
}
```

```bash
curl -s -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d @forecast_sample.json
```

```python
import requests

r = requests.post(
    "http://localhost:8000/forecast",
    json={
        "data": [],  # fill: len >= context_length
        "context_length": 512,
        "forecast_length": 96,
        "request_id": "test123",
    },
    timeout=300,
)
r.raise_for_status()
print(r.json())
```

### Fine-tuning (synchronous)

Minimum **three** rows in `data`:

```json
{
  "data": [
    {
      "date": "2023-01-01 00:00",
      "HUFL": 1.2,
      "HULL": 0.5,
      "MUFL": 1.0,
      "MULL": 0.8,
      "LUFL": 1.1,
      "LULL": 0.7,
      "OT": 1.3
    },
    {
      "date": "2023-01-01 00:10",
      "HUFL": 1.3,
      "HULL": 0.6,
      "MUFL": 1.1,
      "MULL": 0.9,
      "LUFL": 1.2,
      "LULL": 0.8,
      "OT": 1.4
    },
    {
      "date": "2023-01-01 00:20",
      "HUFL": 1.35,
      "HULL": 0.55,
      "MUFL": 1.05,
      "MULL": 0.85,
      "LUFL": 1.15,
      "LULL": 0.75,
      "OT": 1.45
    }
  ],
  "context_length": 512,
  "forecast_length": 96,
  "fewshot_percent": 5.0,
  "freeze_backbone": true,
  "learning_rate": 0.001,
  "num_epochs": 50,
  "batch_size": 64,
  "loss": "mse",
  "quantile": 0.5,
  "request_id": "finetune_test_001"
}
```

```bash
curl -s -X POST http://localhost:8000/finetune \
  -H "Content-Type: application/json" \
  -d @finetune_sample.json
```

### Fine-tuning (async)

```bash
export FINETUNE_ASYNC=true
curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/finetune \
  -H "Content-Type: application/json" \
  -d @finetune_sample.json
curl -s http://localhost:8000/finetune/jobs/<job_id>
```

For heavy training, route work through a real queue (Celery, RQ, Arq); the built-in async mode is a lightweight pattern.

---

## Integrations

### Kafka

1. `docker compose -f docker-compose.yaml up -d --build` — the bundled `app` service enables Kafka and points at `kafka:9092`.
2. Publish JSON to **`forecast_requests`** with the same fields as `POST /forecast`.
3. Consume **`forecast_responses`** for `{ "forecast": ..., "request_id": ... }`.

### Metrics and logs

Scrape **`/metrics`** with Prometheus. Point Grafana at that data source for RED-style panels (`http_requests_total`, forecast counters and latency). Enable **`JSON_LOGS=true`** and ship stdout to Loki or Elasticsearch; correlate with **`X-Request-ID`**.

---

## Deployment

**Image**

```bash
docker build -t chronoapi:latest .
docker run --rm -p 8000:8000 \
  -e SKIP_MODEL_LOAD=0 \
  -e KAFKA_ENABLED=false \
  chronoapi:latest
```

**Compose** — Zookeeper, Kafka (Confluent 7.6.1), and the API on port **8000**: see [`docker-compose.yaml`](docker-compose.yaml).

**Model cache** — Mount **`HF_HOME`** / **`TRANSFORMERS_CACHE`** so weights survive restarts. Offline: pre-seed the cache, then **`TRANSFORMERS_OFFLINE=1`** / **`HF_HUB_OFFLINE=1`** when your policy allows.

**Production** — Terminate TLS in front of the service, set **`API_KEY`** when exposed, rate-limit at the edge, and keep long fine-tunes off the request path.

---

## Contributing

1. Branch from `main` and keep commits focused.
2. Before opening a PR, run the same gates as CI:

   **PowerShell**

   ```powershell
   $env:SKIP_MODEL_LOAD="1"; $env:KAFKA_ENABLED="false"
   pytest; ruff check app tests; ruff format --check app tests; mypy app
   ```

   **Bash**

   ```bash
   export SKIP_MODEL_LOAD=1 KAFKA_ENABLED=false
   pytest && ruff check app tests && ruff format --check app tests && mypy app
   ```

3. CI workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Dependency PRs: [`.github/dependabot.yml`](.github/dependabot.yml).

---

## License

Released under the [MIT License](LICENSE).
