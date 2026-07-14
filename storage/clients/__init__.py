from redis.asyncio import Redis

from storage.clients.messages import MessagesClient
from storage.clients.actions import ActionsClient
from storage.config import redis_config

redis_client = Redis(
    host=redis_config.HOST,
    port=redis_config.PORT,
    password=redis_config.PASSWORD
)

messages_client = MessagesClient(redis_client, redis_config.EXPIRE_KEY_SECONDS)
