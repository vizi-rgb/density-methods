"""Runs the actual ML pipeline (YOLO + lib's heatmap builders) against a real,
short video clip — the one thing unit tests with fake data can't cover: that
the wiring in app/services/pipeline.py still works against real ultralytics
`Results` objects, not just hand-built domain objects.
"""

import itertools
import subprocess

import pytest
from project_root import PROJECT_ROOT

from app.config import Settings
from app.services import pipeline

pytestmark = pytest.mark.integration

_SOURCE_VIDEO = PROJECT_ROOT / "data/datasets/yt/walking_people.mp4"


@pytest.fixture(scope="module")
def short_clip(tmp_path_factory):
    if not _SOURCE_VIDEO.exists():
        pytest.skip(f"sample video not present: {_SOURCE_VIDEO}")

    output = tmp_path_factory.mktemp("clip") / "short_clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(_SOURCE_VIDEO),
            "-t", "1", "-c:v", "libx264", "-an", str(output),
        ],
        check=True,
        capture_output=True,
    )
    return output


def test_pipeline_produces_overlays_for_a_few_real_frames(short_clip) -> None:
    metadata = pipeline.read_metadata(short_clip)
    settings = Settings()

    frames = list(
        itertools.islice(
            pipeline.run(short_clip, metadata, ["directional", "speed", "cluster"], settings),
            5,
        )
    )

    assert len(frames) == 5
    for overlays in frames:
        assert set(overlays) == {"directional", "speed", "cluster"}
        for frame in overlays.values():
            assert frame.shape == (metadata.height, metadata.width, 3)
            assert frame.dtype.name == "uint8"
