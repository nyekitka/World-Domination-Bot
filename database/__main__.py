from sqlalchemy.ext.asyncio import create_async_engine

from database.config import database_config


engine = create_async_engine(
    url=database_config.database_url,
    echo="debug",
    pool_size=database_config.POOL_SIZE,
    pool_timeout=database_config.POOL_TIMEOUT,
)
