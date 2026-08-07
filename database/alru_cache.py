from collections.abc import Awaitable, Callable
from typing import Concatenate, ParamSpec, TypeVar

from asyncache import cached
from cachetools import LRUCache, TTLCache, keys
from sqlalchemy.ext.asyncio import AsyncSession

ParamsType = ParamSpec('ParamsType')
InstanceType = TypeVar('InstanceType')
ReturnType = TypeVar('ReturnType')
SelfType = TypeVar('SelfType')


class _AlruDBCacheWrapper[InstanceType, ParamsType, ReturnType]:
    def __init__(
        self,
        wrapper: AlruDBCacheWrapper,
        instance: InstanceType,
    ):
        self._instance = instance
        self._wrapper = wrapper

    async def __call__(
        self,
        session: AsyncSession,
        *args: ParamsType.args,
        **kwargs: ParamsType.kwargs,
    ) -> ReturnType:
        return await self._wrapper._cached_fn(
            self._instance, session, *args, **kwargs
        )

    def cache_invalidate(
        self,
        *args: ParamsType.args,
        **kwargs: ParamsType.kwargs
    ):
        self._wrapper.cache_invalidate(self._instance, *args, **kwargs)

    def cache_clear(self):
        return self._wrapper.cache_clear()


class AlruDBCacheWrapper[ParamsType, ReturnType]:
    def __init__(
        self,
        fn: Callable[Concatenate[InstanceType, AsyncSession, ParamsType], Awaitable[ReturnType]],
        maxsize: int = 128,
        ttl: float | None = None
    ):
        if ttl is None:
            self.cacher = LRUCache(maxsize)
        else:
            self.cacher = TTLCache(maxsize, ttl)
        self.fn = fn
        self._cached_fn = cached(self.cacher, self._get_key)(self.fn)

    def _get_key(
        self,
        instance: InstanceType,
        session: AsyncSession,
        *args: ParamsType.args,
        **kwargs: ParamsType.kwargs,
    ):
        return keys.hashkey(instance, *args, **kwargs)

    def __get__(
        self, instance: InstanceType, objtype: type | None = None
    ) -> _AlruDBCacheWrapper[InstanceType, ParamsType, ReturnType]:
        return _AlruDBCacheWrapper(self, instance)

    def cache_invalidate(
        self,
        instance: InstanceType,
        *args: ParamsType.args,
        **kwargs: ParamsType.kwargs,
    ):
        key = self._get_key(instance, None, *args, **kwargs)
        if key in self.cacher:
            del self.cacher[key]

    def cache_clear(self):
        self.cacher.clear()


def alru_cache(
    maxsize: int = 128,
    ttl: float | None = None
):
    def wrapper(
        fn: Callable[Concatenate[InstanceType, AsyncSession, ParamsType], Awaitable[ReturnType]]
    ) -> AlruDBCacheWrapper[ParamsType, ReturnType]:
        return AlruDBCacheWrapper(fn, maxsize, ttl)

    return wrapper
