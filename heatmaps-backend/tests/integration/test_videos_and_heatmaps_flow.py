import io

import pytest
from rq import get_current_job

MP4_MAGIC_BYTES = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 100
)


@pytest.fixture(autouse=True)
def _stub_video_normalization(monkeypatch):
    # POST /api/videos transcodes uploads via a real ffmpeg subprocess
    # (app/services/video_normalizer.py) — these tests use synthetic
    # MP4_MAGIC_BYTES with no real video stream, which ffmpeg can't decode.
    # Stub it out so the endpoint's own logic (filetype detection, size
    # limits, storage) is exercised without needing a decodable video.
    async def _fake_normalize_to_mp4(source_path, output_path) -> None:
        output_path.write_bytes(source_path.read_bytes())

    monkeypatch.setattr(
        "app.api.routes.videos.normalize_to_mp4", _fake_normalize_to_mp4
    )


def _fake_process_video(
    job_id, video_path_str, heatmap_request, base_url, transformation_matrix
) -> None:
    job = get_current_job()
    assert job is not None
    job.meta["output"] = {
        "type": heatmap_request["type"],
        "label": f"fake-{heatmap_request['type']}",
        "video_url": f"{base_url}media/jobs/{job_id}/output.mp4",
    }
    job.save_meta()


def _patch_process_video(monkeypatch) -> None:
    import app.worker.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "process_video", _fake_process_video)


def _upload_video(client) -> str:
    response = client.post(
        "/api/videos",
        files={"file": ("clip.mp4", io.BytesIO(MP4_MAGIC_BYTES), "video/mp4")},
    )
    assert response.status_code == 202
    return response.json()["video_id"]


def test_upload_video_returns_video_id_and_url(client) -> None:
    response = client.post(
        "/api/videos",
        files={"file": ("clip.mp4", io.BytesIO(MP4_MAGIC_BYTES), "video/mp4")},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["video_id"]
    assert body["video_url"].endswith(f"/media/videos/{body['video_id']}/source.mp4")


def test_upload_rejects_non_video_file(client) -> None:
    response = client.post(
        "/api/videos",
        files={"file": ("notes.txt", io.BytesIO(b"just some text"), "text/plain")},
    )
    assert response.status_code == 415


def test_upload_rejects_oversized_file(client, settings) -> None:
    settings.max_upload_mb = 0
    oversized = MP4_MAGIC_BYTES + b"\x00" * (2 * 1024 * 1024)
    response = client.post(
        "/api/videos",
        files={"file": ("clip.mp4", io.BytesIO(oversized), "video/mp4")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_create_heatmap_job_and_status_round_trip(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)
    video_id = _upload_video(client)

    response = client.post(
        f"/api/videos/{video_id}/heatmaps",
        json={"type": "directional", "direction": "right"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status = client.get(f"/api/heatmaps/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed"
    assert body["progress"] == 100
    assert body["output"]["type"] == "directional"


def test_create_heatmap_job_for_unknown_video_is_404(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)

    response = client.post(
        "/api/videos/does-not-exist/heatmaps",
        json={"type": "directional", "direction": "right"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "video_not_found"


def test_create_heatmap_job_rejects_bad_direction(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)
    video_id = _upload_video(client)

    response = client.post(
        f"/api/videos/{video_id}/heatmaps",
        json={"type": "directional", "direction": "diagonal"},
    )
    assert response.status_code == 400


def test_create_heatmap_job_rejects_group_size_below_two(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)
    video_id = _upload_video(client)

    response = client.post(
        f"/api/videos/{video_id}/heatmaps",
        json={"type": "cluster", "group_size": 1},
    )
    assert response.status_code == 400


def test_create_heatmap_job_rejects_min_greater_than_max_speed(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)
    video_id = _upload_video(client)

    response = client.post(
        f"/api/videos/{video_id}/heatmaps",
        json={"type": "speed", "min_speed": 10, "max_speed": 2},
    )
    assert response.status_code == 400


def test_create_heatmap_job_rejects_non_positive_half_life_time(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)
    video_id = _upload_video(client)

    response = client.post(
        f"/api/videos/{video_id}/heatmaps",
        json={"type": "directional", "direction": "up", "half_life_time": 0},
    )
    assert response.status_code == 400


def test_status_for_unknown_job_is_404(client) -> None:
    response = client.get("/api/heatmaps/does-not-exist")
    assert response.status_code == 404
