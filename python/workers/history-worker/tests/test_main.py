from pathlib import Path

import pytest

from main import HistoryWorkerConfig, build_history_backend


def test_config_defaults_to_in_memory(monkeypatch) -> None:
    monkeypatch.delenv("HISTORY_BACKEND", raising=False)
    config = HistoryWorkerConfig.from_env(env_path=Path("/tmp/non-existent-history-worker.env"))
    assert config.history_backend == "in_memory"
    assert config.worker_id == "history-worker"


def test_config_from_dotenv_file(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "HISTORY_BACKEND=byclaw\n"
        "BYCLAW_HISTORY_BASE_URL=https://history-from-dotenv.example.com\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("HISTORY_BACKEND", raising=False)
    monkeypatch.delenv("BYCLAW_HISTORY_BASE_URL", raising=False)

    config = HistoryWorkerConfig.from_env(env_path=env_path)

    assert config.history_backend == "byclaw"
    assert config.byclaw_base_url == "https://history-from-dotenv.example.com"


def test_build_history_backend_uses_in_memory() -> None:
    config = HistoryWorkerConfig(history_backend="in_memory")
    backend = build_history_backend(config)
    assert backend.__class__.__name__ == "InMemoryHistoryBackend"


def test_build_history_backend_uses_byclaw(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeBackend:
        def __init__(self, *, base_url: str):
            calls["base_url"] = base_url

    monkeypatch.setattr("main.ByClawHistoryBackend", FakeBackend)

    config = HistoryWorkerConfig(
        history_backend="byclaw",
        byclaw_base_url="https://history.example.com",
    )
    build_history_backend(config)

    assert calls["base_url"] == "https://history.example.com"


def test_build_history_backend_uses_postgres(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeBackend:
        def __init__(self, *, dsn: str):
            calls["dsn"] = dsn

    monkeypatch.setattr("main.PostgresHistoryBackend", FakeBackend)

    config = HistoryWorkerConfig(
        history_backend="postgres",
        postgres_dsn="postgresql://u:p@localhost:5432/db",
    )
    build_history_backend(config)

    assert calls["dsn"] == "postgresql://u:p@localhost:5432/db"


def test_build_history_backend_requires_byclaw_base_url() -> None:
    config = HistoryWorkerConfig(history_backend="byclaw", byclaw_base_url=None)
    with pytest.raises(ValueError, match="BYCLAW_HISTORY_BASE_URL"):
        build_history_backend(config)


def test_build_history_backend_requires_postgres_dsn() -> None:
    config = HistoryWorkerConfig(history_backend="postgres", postgres_dsn=None)
    with pytest.raises(ValueError, match="BYAI_HISTORY_PG_DSN"):
        build_history_backend(config)
