import numpy as np
from core.helpers.camera_info import CameraInfo
from rq import get_current_job

from app.services.storage import finalize_video_path, new_id

_CAMERA_POINTS = [[0, 0], [0, 100], [100, 100], [100, 0]]
_REAL_WORLD_POINTS = [[0, 0], [0, 5], [5, 5], [5, 0]]


def _create_video(settings) -> str:
    # Bypasses POST /api/videos (real upload/transcode) — these tests only
    # exercise calibration/matrix wiring, which just needs a source file to
    # exist at the path video_source_path() checks for.
    video_id = new_id()
    finalize_video_path(settings, video_id, ".mp4").write_bytes(b"fake video bytes")
    return video_id


def _capture_process_video(monkeypatch):
    calls: list[list[list[float]]] = []

    def _fake_process_video(job_id, video_path_str, heatmap_request, base_url, transformation_matrix):
        calls.append(transformation_matrix)
        job = get_current_job()
        assert job is not None
        job.meta["output"] = {
            "type": heatmap_request["type"],
            "label": f"fake-{heatmap_request['type']}",
            "video_url": f"{base_url}media/jobs/{job_id}/output.mp4",
        }
        job.save_meta()

    import app.worker.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "process_video", _fake_process_video)
    return calls


def test_set_calibration_succeeds_for_known_video(client, settings) -> None:
    video_id = _create_video(settings)

    response = client.post(
        f"/api/videos/{video_id}/calibration",
        json={"camera_points": _CAMERA_POINTS, "real_world_points": _REAL_WORLD_POINTS},
    )

    assert response.status_code == 204


def test_set_calibration_for_unknown_video_is_404(client) -> None:
    response = client.post(
        "/api/videos/does-not-exist/calibration",
        json={"camera_points": _CAMERA_POINTS, "real_world_points": _REAL_WORLD_POINTS},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "video_not_found"


def test_set_calibration_rejects_wrong_point_count(client, settings) -> None:
    video_id = _create_video(settings)

    response = client.post(
        f"/api/videos/{video_id}/calibration",
        json={"camera_points": _CAMERA_POINTS[:3], "real_world_points": _REAL_WORLD_POINTS},
    )

    assert response.status_code == 400


def test_set_calibration_rejects_degenerate_points(client, settings) -> None:
    video_id = _create_video(settings)
    collinear_points = [[0, 0], [1, 1], [2, 2], [3, 3]]

    response = client.post(
        f"/api/videos/{video_id}/calibration",
        json={"camera_points": collinear_points, "real_world_points": _REAL_WORLD_POINTS},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_calibration_points"


def test_heatmap_job_uses_calibrated_matrix(client, settings, monkeypatch) -> None:
    calls = _capture_process_video(monkeypatch)
    video_id = _create_video(settings)
    client.post(
        f"/api/videos/{video_id}/calibration",
        json={"camera_points": _CAMERA_POINTS, "real_world_points": _REAL_WORLD_POINTS},
    ).raise_for_status()

    response = client.post(
        f"/api/videos/{video_id}/heatmaps",
        json={"type": "directional", "direction": "right"},
    )
    assert response.status_code == 202

    assert len(calls) == 1
    expected = cv2_matrix()
    assert np.allclose(calls[0], expected)


def test_heatmap_job_falls_back_to_default_matrix_when_uncalibrated(
    client, settings, monkeypatch
) -> None:
    calls = _capture_process_video(monkeypatch)
    video_id = _create_video(settings)

    response = client.post(
        f"/api/videos/{video_id}/heatmaps",
        json={"type": "directional", "direction": "right"},
    )
    assert response.status_code == 202

    assert len(calls) == 1
    assert np.allclose(calls[0], CameraInfo().get_transformation_matrix())


def cv2_matrix() -> np.ndarray:
    import cv2

    return cv2.getPerspectiveTransform(
        np.array(_CAMERA_POINTS, dtype=np.float32),
        np.array(_REAL_WORLD_POINTS, dtype=np.float32),
    )
