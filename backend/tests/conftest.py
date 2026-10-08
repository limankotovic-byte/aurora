import io
import logging
import os
import socket
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import JsonFormatter
from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in tuple(os.environ):
        if name.startswith("AURORA_"):
            monkeypatch.delenv(name)

    def block_connect(_socket: socket.socket, _address: object) -> None:
        raise AssertionError("Unit/API tests must not connect to a network")

    monkeypatch.setattr(socket.socket, "connect", block_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", block_connect)


@pytest.fixture
def app() -> FastAPI:
    return create_app(Settings(environment="test", catalog_provider="none"))


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def log_output(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    monkeypatch.setattr(logging.getLogger("aurora"), "handlers", [handler])
    return output
