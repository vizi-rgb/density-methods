import io

from rq import get_current_job

MP4_MAGIC_BYTES = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 100
)


def _fake_process_video(job_id, heatmap_types, video_path_str, base_url) -> None:
    job = get_current_job()
    assert job is not None
    job.meta["outputs"] = [
        {
            "type": heatmap_type,
            "label": heatmap_type,
            "manifest_url": f"{base_url}media/{job_id}/{heatmap_type}/stream.m3u8",
        }
        for heatmap_type in heatmap_types
    ]
    job.save_meta()


def _patch_process_video(monkeypatch) -> None:
    import app.worker.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "process_video", _fake_process_video)


def test_upload_and_status_round_trip(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)

    response = client.post(
        "/api/upload",
        files={"file": ("clip.mp4", io.BytesIO(MP4_MAGIC_BYTES), "video/mp4")},
        data={"heatmap_types": ["directional", "speed"]},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status = client.get(f"/api/status/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed"
    assert body["progress"] == 100
    assert {o["type"] for o in body["outputs"]} == {"directional", "speed"}


def test_upload_rejects_empty_heatmap_types(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)

    response = client.post(
        "/api/upload",
        files={"file": ("clip.mp4", io.BytesIO(MP4_MAGIC_BYTES), "video/mp4")},
        data={"heatmap_types": []},
    )
    assert response.status_code == 400


def test_upload_rejects_unknown_heatmap_type(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)

    response = client.post(
        "/api/upload",
        files={"file": ("clip.mp4", io.BytesIO(MP4_MAGIC_BYTES), "video/mp4")},
        data={"heatmap_types": ["roi"]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_heatmap_types"


def test_upload_rejects_non_video_file(client, monkeypatch) -> None:
    _patch_process_video(monkeypatch)

    response = client.post(
        "/api/upload",
        files={"file": ("notes.txt", io.BytesIO(b"just some text"), "text/plain")},
        data={"heatmap_types": ["directional"]},
    )
    assert response.status_code == 415


def test_status_for_unknown_job_is_404(client) -> None:
    response = client.get("/api/status/does-not-exist")
    assert response.status_code == 404


def test_upload_rejects_oversized_file(client, settings, monkeypatch) -> None:
    _patch_process_video(monkeypatch)
    monkeypatch.setattr(settings, "max_upload_mb", 0)

    oversized = MP4_MAGIC_BYTES + b"\x00" * (2 * 1024 * 1024)
    response = client.post(
        "/api/upload",
        files={"file": ("clip.mp4", io.BytesIO(oversized), "video/mp4")},
        data={"heatmap_types": ["directional"]},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
