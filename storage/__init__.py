from redis import Redis

from storage.config import redis_config

redis_client = Redis(
    db=redis_config.DB,
    username=redis_config.USER,
    host=redis_config.HOST,
    port=redis_config.PORT,
    password=redis_config.PASSWORD,
)
