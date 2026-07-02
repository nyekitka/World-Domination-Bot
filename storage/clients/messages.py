from redis import Redis

from storage.clients.base import BaseClient
from storage.schemas import MessageType, INFO_MESSAGE_TYPES, PLANET_MESSAGE_TYPES


class MessagesClient(BaseClient):
    def __init__(self, redis_client: Redis, ex: int):
        super().__init__(redis_client, ex)

    def get_info_message_id(
        self, owner_id: int, message_type: MessageType
    ) -> int | None:
        result = self.get('info', message_type, owner_id)
        if result:
            return int(result)
        
        return result
    
    def delete_info_message_id(
        self, owner_id: int, message_type: MessageType
    ) -> bool:
        return self.delete('info', message_type, owner_id)
    
    def set_info_message_id(
        self, owner_id: int, message_type: MessageType, message_id: int
    ) -> bool:
        return self.set(message_id, 'info', message_type, owner_id)

    def get_planet_message_id(
        self, owner_id: int, message_type: MessageType, planet_id: int, 
    ) -> int | None:
        result = self.hget(planet_id, 'planet', message_type, owner_id)
        if result:
            return int(result)
        
        return result
    
    def delete_planet_message_ids(
        self, owner_id: int, message_type: MessageType, *planet_ids: int, 
    ) -> bool:
        str_planet_ids = list(map(str, planet_ids))
        return self.hdel(str_planet_ids, 'planet', message_type, owner_id)

    def set_planet_message_id(
        self,
        owner_id: int,
        planet_id: int,
        message_type: MessageType,
        message_id: int,
    ) -> bool:
        return self.hset(planet_id, message_id, 'planet', message_type, owner_id)

    def find_all_messages(
        self, owner_id: int
    ) -> list[int]:
        message_ids = []

        for message_type in INFO_MESSAGE_TYPES:
            message_id = self.get_info_message_id(owner_id, message_type)
            if message_id:
                message_ids.append(message_id)
        
        for message_type in PLANET_MESSAGE_TYPES:
            messages = self.hgetall('planet', message_type, owner_id)
            if messages:
                message_ids.extend(messages.values())

        return list(map(int, message_ids))
    
    def delete_all_messages(
        self, owner_id: int
    ) -> None:
        for message_type in INFO_MESSAGE_TYPES:
            self.delete_info_message_id(owner_id, message_type)
        
        for message_type in PLANET_MESSAGE_TYPES:
            self.delete('planet', message_type, owner_id)
