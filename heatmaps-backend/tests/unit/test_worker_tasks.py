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
_HEATMAP_REQUEST = {"type": "directional", "direction": "right"}
_MATRIX = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def test_run_job_success_sets_progress_and_output(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tasks_module.pipeline, "read_metadata", lambda path: _METADATA)
    monkeypatch.setattr(
        tasks_module.pipeline,
        "run",
        lambda video_path, metadata, heatmap_request, settings, transformation_matrix: iter(
            [_FRAME, _FRAME]
        ),
    )
    monkeypatch.setattr(tasks_module, "Mp4Encoder", _FakeEncoder)

    job = _FakeJob()
    settings = Settings(data_dir=tmp_path)

    tasks_module.run_job(
        job,
        "job-1",
        Path("/fake/video.mp4"),
        _HEATMAP_REQUEST,
        "http://x/",
        _MATRIX,
        settings,
    )

    assert job.meta["progress"] == 100
    assert job.meta["output"]["type"] == "directional"
    assert job.meta["output"]["label"] == "Directional — right"
    assert job.meta["output"]["video_url"] == "http://x/media/jobs/job-1/output.mp4"
    assert len(_FakeEncoder.instances) == 1
    encoder = _FakeEncoder.instances[0]
    assert encoder.closed and not encoder.killed
    assert len(encoder.frames_written) == 2


def test_run_job_success_uses_composed_label_for_composed_requests(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(tasks_module.pipeline, "read_metadata", lambda path: _METADATA)
    monkeypatch.setattr(
        tasks_module.pipeline,
        "run",
        lambda video_path, metadata, heatmap_request, settings, transformation_matrix: iter(
            [_FRAME]
        ),
    )
    monkeypatch.setattr(tasks_module, "Mp4Encoder", _FakeEncoder)

    composed_request = {
        "type": "composed",
        "layers": [
            {"heatmap": {"type": "speed", "min_speed": 7}},
            {
                "heatmap": {"type": "directional", "direction": "up"},
                "operator": "AND",
            },
        ],
    }
    job = _FakeJob()
    settings = Settings(data_dir=tmp_path)

    tasks_module.run_job(
        job,
        "job-composed",
        Path("/fake/video.mp4"),
        composed_request,
        "http://x/",
        _MATRIX,
        settings,
    )

    assert job.meta["output"]["type"] == "composed"
    assert job.meta["output"]["label"] == (
        "Show tracks matching (Speed ≥7 km/h) AND (Moving Up)"
    )


def test_run_job_failure_records_error_and_kills_encoder(tmp_path, monkeypatch) -> None:
    def _failing_run(video_path, metadata, heatmap_request, settings, transformation_matrix):
        yield _FRAME
        raise RuntimeError("model exploded")

    monkeypatch.setattr(tasks_module.pipeline, "read_metadata", lambda path: _METADATA)
    monkeypatch.setattr(tasks_module.pipeline, "run", _failing_run)
    monkeypatch.setattr(tasks_module, "Mp4Encoder", _FakeEncoder)

    job = _FakeJob()
    settings = Settings(data_dir=tmp_path)

    with pytest.raises(RuntimeError, match="model exploded"):
        tasks_module.run_job(
            job,
            "job-2",
            Path("/fake/video.mp4"),
            _HEATMAP_REQUEST,
            "http://x/",
            _MATRIX,
            settings,
        )

    assert job.meta["error"] == "model exploded"
    assert "output" not in job.meta
    assert len(_FakeEncoder.instances) == 1
    encoder = _FakeEncoder.instances[0]
    assert encoder.killed and not encoder.closed
