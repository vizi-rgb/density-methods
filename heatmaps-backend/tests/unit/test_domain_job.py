from rq.job import Job
from rq.job import JobStatus as RQJobStatus

from app.domain.job import JobState, JobStatus, build_label


def _noop() -> None:
    return None


def test_freshly_created_job_is_queued(fake_redis) -> None:
    job = Job.create(_noop, id="job-1", connection=fake_redis)
    job.save()

    state = JobState.from_rq_job(job)

    assert state == JobState(status=JobStatus.QUEUED)


def test_started_job_reports_progress_from_meta(fake_redis) -> None:
    job = Job.create(_noop, id="job-2", connection=fake_redis, meta={"progress": 0})
    job.save()
    job.set_status(RQJobStatus.STARTED)
    job.meta["progress"] = 37
    job.save_meta()

    state = JobState.from_rq_job(Job.fetch("job-2", connection=fake_redis))

    assert state == JobState(status=JobStatus.PROCESSING, progress=37)


def test_finished_job_reports_output_and_full_progress(fake_redis) -> None:
    job = Job.create(_noop, id="job-3", connection=fake_redis)
    job.save()
    job.set_status(RQJobStatus.FINISHED)
    job.meta["output"] = {
        "type": "directional",
        "label": "Directional — right",
        "video_url": "http://x/y.mp4",
    }
    job.save_meta()

    state = JobState.from_rq_job(Job.fetch("job-3", connection=fake_redis))

    assert state.status == JobStatus.COMPLETED
    assert state.progress == 100
    assert state.output is not None
    assert state.output.type == "directional"
    assert state.output.video_url == "http://x/y.mp4"


def test_failed_job_reports_error_from_meta(fake_redis) -> None:
    job = Job.create(_noop, id="job-4", connection=fake_redis)
    job.save()
    job.set_status(RQJobStatus.FAILED)
    job.meta["error"] = "unsupported codec"
    job.save_meta()

    state = JobState.from_rq_job(Job.fetch("job-4", connection=fake_redis))

    assert state == JobState(status=JobStatus.FAILED, error="unsupported codec")


def test_failed_job_without_meta_error_gets_fallback_message(fake_redis) -> None:
    job = Job.create(_noop, id="job-5", connection=fake_redis)
    job.save()
    job.set_status(RQJobStatus.FAILED)

    state = JobState.from_rq_job(Job.fetch("job-5", connection=fake_redis))

    assert state.status == JobStatus.FAILED
    assert state.error


def test_build_label_directional() -> None:
    assert build_label({"type": "directional", "direction": "right"}) == "Directional — right"


def test_build_label_speed_variants() -> None:
    assert build_label({"type": "speed"}) == "Speed (any)"
    assert build_label({"type": "speed", "min_speed": 3.5}) == "Speed ≥3.5 km/h"
    assert build_label({"type": "speed", "max_speed": 10}) == "Speed ≤10 km/h"
    assert (
        build_label({"type": "speed", "min_speed": 3.5, "max_speed": 10})
        == "Speed 3.5–10 km/h"
    )


def test_build_label_cluster() -> None:
    assert build_label({"type": "cluster", "group_size": 3}) == "Cluster size 3"
