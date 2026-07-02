from typing import Any, Set

from redis import Redis


class BaseClient:
    def __init__(self, client: Redis, ex: int, sep: str = ':'):
        self.client = client
        self.ex = ex
        self.sep = sep
    
    def _create_name(self, *args: Any) -> str:
        return self.sep.join(list(map(str, args)))
    
    def set(self, value: Any, *name_args: Any) -> bool:
        name = self._create_name(*name_args)
        return bool(
            self.client.set(
                name=name,
                value=str(value),
                ex=self.ex
            )
        )
    
    def get(self, *name_args: Any) -> Any:
        name = self._create_name(*name_args)
        return self.client.get(name)
    
    def delete(self, *name_args: Any) -> None:
        name = self._create_name(*name_args)
        self.client.delete(name)
    
    def hset(self, key: Any, value: Any, *name_args: Any) -> bool:
        name = self._create_name(*name_args)
        return bool(
            self.client.hset(
                name, str(key), str(value)
            )
        )
    
    def hget(self, key: Any, *name_args: Any) -> Any:
        name = self._create_name(*name_args)
        return self.client.hget(name, str(key))
    
    def hgetall(self, *name_args: Any) -> dict[str, Any]:
        name = self._create_name(*name_args)
        return self.client.hgetall(name)
    
    def hdel(self, keys: list[Any], *name_args: Any) -> bool:
         name = self._create_name(*name_args)
         return bool(self.client.hdel(name, *keys))

    def sadd(self, items: list[Any], *name_args: Any) -> int:
        items = list(map(str, items))
        name = self._create_name(*name_args)
        return self.client.sadd(name, *items)
    
    def sdel(self, items: list[Any], *name_args: Any) -> int:
        items = list(map(str, items))
        name = self._create_name(*name_args)
        return self.client.srem(name, *items)
    
    def smembers(self, *name_args: Any) -> Set[Any]:
        name = self._create_name(*name_args)
        return self.client.smembers(name)

    def sismember(self, value: Any, *name_args: Any) -> bool:
        name = self._create_name(*name_args)
        return bool(self.client.sismember(name, str(value)))

    def exists(self, *name_args: Any) -> bool:
        name = self._create_name(*name_args)
        return bool(self.client.exists(name))