from pathlib import Path

import numpy as np
import pytest
from core.helpers.data_source_info import DataSourceInfo

import app.worker.tasks as tasks_module
from app.config import Settings


class _FakeJob:
    def __init__(self) -> None:
        self.meta: dict = {}
        self.save_meta_calls = 0

    def save_meta(self) -> None:
        self.save_meta_calls += 1


class _FakeEncoder:
    instances: list["_FakeEncoder"] = []

    def __init__(self, **kwargs) -> None:
        self.closed = False
        self.killed = False
        self.frames_written: list[np.ndarray] = []
        _FakeEncoder.instances.append(self)

    def write_frame(self, frame: np.ndarray) -> None:
        self.frames_written.append(frame)

    def close(self) -> None:
        self.closed = True

    def kill(self) -> None:
        self.killed = True


@pytest.fixture(autouse=True)
def _reset_fake_encoder_instances():
    _FakeEncoder.instances = []
    yield
    _FakeEncoder.instances = []


_METADATA = DataSourceInfo(height=4, width=4, frames=2, fps=10)
_FRAME = np.zeros((4, 4, 3), dtype=np.uint8)


def test_run_job_success_sets_progress_and_outputs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tasks_module.pipeline, "read_metadata", lambda path: _METADATA)
    monkeypatch.setattr(
        tasks_module.pipeline,
        "run",
        lambda video_path, metadata, heatmap_types, settings: iter(
            [{t: _FRAME for t in heatmap_types}, {t: _FRAME for t in heatmap_types}]
        ),
    )
    monkeypatch.setattr(tasks_module, "HlsEncoder", _FakeEncoder)

    job = _FakeJob()
    settings = Settings(data_dir=tmp_path)

    tasks_module.run_job(
        job, "job-1", ["directional", "speed"], Path("/fake/video.mp4"), "http://x/", settings
    )

    assert job.meta["progress"] == 100
    assert {o["type"] for o in job.meta["outputs"]} == {"directional", "speed"}
    assert all(o["manifest_url"].startswith("http://x/media/job-1/") for o in job.meta["outputs"])
    assert all(encoder.closed and not encoder.killed for encoder in _FakeEncoder.instances)


def test_run_job_failure_records_error_and_kills_encoders(tmp_path, monkeypatch) -> None:
    def _failing_run(video_path, metadata, heatmap_types, settings):
        yield {t: _FRAME for t in heatmap_types}
        raise RuntimeError("model exploded")

    monkeypatch.setattr(tasks_module.pipeline, "read_metadata", lambda path: _METADATA)
    monkeypatch.setattr(tasks_module.pipeline, "run", _failing_run)
    monkeypatch.setattr(tasks_module, "HlsEncoder", _FakeEncoder)

    job = _FakeJob()
    settings = Settings(data_dir=tmp_path)

    with pytest.raises(RuntimeError, match="model exploded"):
        tasks_module.run_job(
            job, "job-2", ["directional"], Path("/fake/video.mp4"), "http://x/", settings
        )

    assert job.meta["error"] == "model exploded"
    assert "outputs" not in job.meta
    assert all(encoder.killed and not encoder.closed for encoder in _FakeEncoder.instances)
