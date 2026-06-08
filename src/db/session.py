from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings


def _build_engine_url(url: str) -> str:
    # asyncpg doesn't accept sslmode/channel_binding as URL params
    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()
              if k not in ("sslmode", "channel_binding")}
    return urlunparse(parsed._replace(query=urlencode(params)))


engine = create_async_engine(
    _build_engine_url(settings.database_url),
    connect_args={"ssl": True},
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
