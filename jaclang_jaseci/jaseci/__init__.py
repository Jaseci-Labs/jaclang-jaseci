"""Jaseci FastAPI."""

from contextlib import asynccontextmanager
from os import getenv
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI as _FaststAPI

from uvicorn import run as _run


class FastAPI:
    """FastAPI Handler."""

    __app__ = None

    @classmethod
    def get(cls) -> _FaststAPI:
        """Get or Create new instance of FastAPI."""
        if not isinstance(cls.__app__, _FaststAPI):

            @asynccontextmanager
            async def lifespan(app: _FaststAPI) -> AsyncGenerator[None, _FaststAPI]:
                from .datasources import Collection

                await Collection.apply_indexes()
                yield

            cls.__app__ = _FaststAPI(lifespan=lifespan)

            from .routers import healthz_router, sso_router, user_router
            from ..plugin.jaseci import walker_router

            for router in [healthz_router, sso_router, user_router, walker_router]:
                cls.__app__.include_router(router)

        return cls.__app__

    @classmethod
    def start(
        cls,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs: Any  # noqa ANN401
    ) -> None:
        """Run FastAPI Handler via Uvicorn."""
        _run(
            cls.get(),
            host=host or getenv("HOST") or "0.0.0.0",
            port=port or int(getenv("HOST", "8000")),
            **kwargs
        )
