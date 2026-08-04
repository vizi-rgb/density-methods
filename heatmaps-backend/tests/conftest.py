from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient
from rq import Queue

from app.config import get_settings
from app.worker import queue as worker_queue


@pytest.fixture
def fake_redis():
    return fakeredis.FakeStrictRedis()


@pytest.fixture
def sync_queue(fake_redis, monkeypatch):
    """A queue whose `.enqueue()` runs the job synchronously in-process,
    against a fakeredis connection — no real Redis or worker process needed."""
    queue = Queue(worker_queue.QUEUE_NAME, connection=fake_redis, is_async=False)
    monkeypatch.setattr(worker_queue, "get_redis", lambda: fake_redis)
    monkeypatch.setattr(worker_queue, "get_queue", lambda: queue)
    return queue


@pytest.fixture
def settings(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("data_dir", str(tmp_path))
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def client(sync_queue, settings):
    from app.main import create_app

    return TestClient(create_app())
