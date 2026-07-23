from datetime import datetime
from typing import (
    Any, Awaitable, Callable, ParamSpec
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

P = ParamSpec('P')


class Notifier:
    def __init__(
        self,
        loop_length: int,
        checkpoints: dict[str, int],
        handlers: dict[str, Callable[P, Awaitable[None]]],
        handler_args: dict[str, tuple[Any]],
        handler_kwargs: dict[str, dict[str, Any]],
    ):
        checkpoints.sort()
        assert (
            checkpoints[0] > 0
            and checkpoints[-1] < loop_length
        )

        self.loop_length = loop_length
        self.checkpoints = checkpoints
        self.handlers = handlers
        self.args = handler_args
        self.kwargs = handler_kwargs

    async def run_loop(self):
        scheduler = AsyncIOScheduler()
        scheduler.start()
        now = datetime.now()

        async def executor(key: str):
            await self.handlers[key](
                *self.args[key],
                **self.kwargs[key],
            )

        for key, secs in self.checkpoints.items():
            scheduler.add_job(
                func=executor,
                trigger=DateTrigger(now + datetime.timedelta(seconds=secs)),
                args=(key,)
            )
