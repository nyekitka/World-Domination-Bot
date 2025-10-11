from redis.asyncio import Redis

from storage.schemas import MessageType

class MessagesClient:
    def __init__(self, redis_client: Redis, ex: int):
        self.client = redis_client
        self.ex = ex
    
    def _make_info_message_key(
        self, owner_id: int, message_type: MessageType
    ) -> str:
        return f'info:{message_type}:{owner_id}'
    
    def _make_planet_message_key(
        self, owner_id: int, planet_id: int, message_type: MessageType
    ) -> str:
        return f'planet:{message_type}:{owner_id}:{planet_id}'

    def get_info_message_id(
        self, owner_id: int, message_type: MessageType
    ) -> int | None:
        key = self._make_info_message_key(owner_id, message_type)

        result = self.client.get(key)
        if result:
            return int(result)
        
        return result
    
    def set_info_message_id(
        self, owner_id: int, message_type: MessageType, message_id: int
    ) -> bool:
        key = self._make_info_message_key(owner_id, message_type)

        return bool(
            self.client.set(
                name=key,
                value=str(message_id),
                ex=self.ex
            )
        )

    def get_planet_message_id(
        self, owner_id: int, planet_id: int, message_type: MessageType
    ) -> int | None:
        key = self._make_planet_message_key(
            owner_id, planet_id, message_type
        )

        result = self.client.get(key)
        if result:
            return int(result)
        
        return result

    def set_planet_message_id(
        self,
        owner_id: int,
        planet_id: int,
        message_type: MessageType,
        message_id: int,
    ) -> bool:
        key = self._make_planet_message_key(owner_id, planet_id, message_type)

        return bool(
            self.client.set(
                name=key,
                value=str(message_id),
                ex=self.ex
            )
        )
