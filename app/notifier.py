import datetime
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

P = ParamSpec('P')


class Notifier:
    def __init__(
        self,
        checkpoints: dict[int, str],
        handlers: dict[str, Callable[P, Awaitable[None]]],
        handler_args: dict[str, tuple[Any]] = (),
        handler_kwargs: dict[str, dict[str, Any]] | None = None,
    ):
        if handler_kwargs is None:
            handler_kwargs = {}
        min_checkpoint = min(checkpoints.keys())
        assert min_checkpoint > 0

        self.checkpoints = checkpoints
        self.handlers = handlers
        self.args = handler_args
        self.kwargs = handler_kwargs

    async def run_loop(self):
        scheduler = AsyncIOScheduler()
        scheduler.start()
        now = datetime.datetime.now(
            tz=ZoneInfo('Europe/Moscow')
        )

        async def executor(key: str):
            await self.handlers[key](
                *self.args.get(key, ()),
                **self.kwargs.get(key, {}),
            )

        for secs, key in self.checkpoints.items():
            scheduler.add_job(
                func=executor,
                trigger=DateTrigger(now + datetime.timedelta(seconds=secs)),
                args=(key,),
            )
