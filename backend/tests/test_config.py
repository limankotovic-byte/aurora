from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_environment_overrides_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("AURORA_HTTP_TIMEOUT_SECONDS=8\n", encoding="utf-8")
    assert Settings().http_timeout_seconds == 8
    monkeypatch.setenv("AURORA_HTTP_TIMEOUT_SECONDS", "3.5")
    assert Settings().http_timeout_seconds == 3.5
    assert Settings(http_timeout_seconds=2).http_timeout_seconds == 2


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AURORA_HTTP_TIMEOUT_SECONDS", "0"),
        ("AURORA_HTTP_TIMEOUT_SECONDS", "nan"),
        ("AURORA_HTTP_MAX_CONNECTIONS", "0"),
        ("AURORA_LOG_LEVEL", "invalid"),
        ("AURORA_ENVIRONMENT", "invalid"),
    ],
)
def test_invalid_settings_fail_fast(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings()


def test_inconsistent_connection_limits_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Keepalive"):
        Settings(http_max_connections=2, http_max_keepalive_connections=3)
