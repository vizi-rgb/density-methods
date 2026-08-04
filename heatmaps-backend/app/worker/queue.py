from functools import lru_cache

from redis import Redis
from rq import Queue

from app.config import get_settings

QUEUE_NAME = "video-processing"


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis())
