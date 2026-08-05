import datetime
from typing import (
    Any, Awaitable, Callable, ParamSpec
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from game.config import game_config

P = ParamSpec('P')


class Notifier:
    def __init__(
        self,
        checkpoints: dict[int, str],
        handlers: dict[str, Callable[P, Awaitable[None]]],
        handler_args: dict[str, tuple[Any]] = tuple(),
        handler_kwargs: dict[str, dict[str, Any]] = dict(),
    ):
        min_checkpoint = min(checkpoints.keys())
        assert min_checkpoint > 0

        self.checkpoints = checkpoints
        self.handlers = handlers
        self.args = handler_args
        self.kwargs = handler_kwargs

    async def run_loop(self):
        scheduler = AsyncIOScheduler()
        scheduler.start()
        now = datetime.datetime.now()

        async def executor(key: str):
            await self.handlers[key](
                *self.args.get(key, tuple()),
                **self.kwargs.get(key, dict()),
            )

        for secs, key in self.checkpoints.items():
            scheduler.add_job(
                func=executor,
                trigger=DateTrigger(now + datetime.timedelta(seconds=secs)),
                args=(key,)
            )
