from redis import Redis

from storage.config import redis_config

redis_client = Redis(
    db=redis_config.DB,
    host=redis_config.HOST,
    port=redis_config.INNER_PORT,
    password=redis_config.PASSWORD,
)
