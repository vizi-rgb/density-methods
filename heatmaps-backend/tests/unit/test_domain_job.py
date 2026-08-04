from rq.job import Job
from rq.job import JobStatus as RQJobStatus

from app.domain.job import JobState, JobStatus


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


def test_finished_job_reports_outputs_and_full_progress(fake_redis) -> None:
    job = Job.create(_noop, id="job-3", connection=fake_redis)
    job.save()
    job.set_status(RQJobStatus.FINISHED)
    job.meta["outputs"] = [
        {"type": "directional", "label": "Directional flow", "manifest_url": "http://x/y.m3u8"}
    ]
    job.save_meta()

    state = JobState.from_rq_job(Job.fetch("job-3", connection=fake_redis))

    assert state.status == JobStatus.COMPLETED
    assert state.progress == 100
    assert state.outputs is not None
    assert state.outputs[0].type == "directional"
    assert state.outputs[0].manifest_url == "http://x/y.m3u8"


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
