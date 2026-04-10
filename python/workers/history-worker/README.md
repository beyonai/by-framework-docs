# history-worker

A minimal `by-framework` + LangGraph worker sample that demonstrates how to plug different history backends into `run_worker`.

## Supported History Backends

- `in_memory`
- `byclaw`
- `postgres`

## Setup

```bash
cd /Users/xiaozhongcheng/data/company/beyonai/by-framework-samples/python/workers/history-worker
uv sync --extra dev
```

The worker automatically loads environment variables from `.env` in the current directory.

## Environment

Common variables:

```bash
export WORKER_ID="history-worker"
export WORKER_CAPABILITY="history_worker"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"
export WORKSPACE_DIR="/tmp/by-framework-samples"
export CONSUMER_GROUP="agent_engines"
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o"
```

Use in-memory history:

```bash
export HISTORY_BACKEND="in_memory"
```

Use ByClaw history:

```bash
export HISTORY_BACKEND="byclaw"
export BYCLAW_HISTORY_BASE_URL="https://history.example.com"
```

Use PostgreSQL history:

```bash
export HISTORY_BACKEND="postgres"
export BYAI_HISTORY_PG_DSN="postgresql://user:pass@localhost:5432/db"
```

## Run

```bash
uv run python main.py
```

## Behavior

The worker reads recent session history through the configured backend and prepends it to the LangGraph prompt as context before answering.
