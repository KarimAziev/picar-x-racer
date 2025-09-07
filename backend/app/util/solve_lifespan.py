from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator, Callable, TypeVar

from fastapi import FastAPI, Request
from fastapi.dependencies.utils import get_dependant, solve_dependencies

T = TypeVar("T")


def solve_lifespan(
    lifespan: Callable[..., AsyncGenerator[T, None]]
) -> Callable[[FastAPI], AsyncContextManager[T]]:
    @asynccontextmanager
    async def _solve_lifespan(app: FastAPI) -> AsyncGenerator[T, None]:
        """
        Wrap a lifespan dependency generator function so that it can be used as an async context manager
        within a FastAPI lifespan context.

        FastAPI's dependency injection is primarily designed for HTTP request contexts. This function provides
        a workaround by creating a fake Request instance, allowing you to use dependency injection in your
        lifespan startup/shutdown events. The supplied `lifespan` callable should be an async generator (i.e.,
        a function using "yield" along with dependency declarations via Depends) that yields a resource
        (or a collection of resources) to be used during your application's lifespan.

        Parameters:
            lifespan (Callable[..., AsyncGenerator[T, None]]):
                An async generator function that defines your lifespan dependencies. This function can declare
                parameters with FastAPI’s dependency injection (using Depends) and should yield a value of type T.

        Returns:
            Callable[[FastAPI], AsyncContextManager[T]]:
                A callable that takes a FastAPI application instance and returns an asynchronous context manager.
                When entered, the context manager yields the value produced by the lifespan dependency function,
                with all of its dependencies resolved via FastAPI.

        Usage Example:
            # Define a lifespan dependency:
            async def get_lifespan_dependencies(
                connection_manager: ConnectionService = Depends(get_connection_service),
                detection_manager: DetectionService = Depends(get_detection_service),
                music_manager: MusicService = Depends(get_music_service),
            ) -> AsyncGenerator[LifespanAppDeps, None]:
                deps: LifespanAppDeps = {
                    "connection_manager": connection_manager,
                    "detection_manager": detection_manager,
                    "music_manager": music_manager,
                }
                yield deps

            # Wrap the lifespan dependency:
            lifespan_deps = solve_lifespan(get_lifespan_dependencies)
            async with lifespan_deps(app) as deps:
                app.state.connection_manager = deps["connection_manager"]
                # Continue with additional logic...

        Note:
            This implementation uses a fake Request with minimal information (including a custom header to indicate
            lifespan usage) so that FastAPI’s dependency system can operate. Be cautious, as this is essentially a hack
            to utilize the dependency system outside its normal HTTP context.
        """
        fake_request = Request(
            scope={
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/",
                "raw_path": b"/",
                "query_string": b"",
                "root_path": "",
                "headers": ((b"X-Request-Scope", b"lifespan"),),
                "client": ("localhost", 80),
                "server": ("localhost", 80),
                "state": app.state,
            }
        )
        dependant = get_dependant(path="/", call=lifespan)
        async with AsyncExitStack() as async_exit_stack:
            solved = await solve_dependencies(
                request=fake_request,
                dependant=dependant,
                async_exit_stack=async_exit_stack,
                embed_body_fields=False,
            )
            # Create a context manager from the lifespan function.
            ctxmgr = asynccontextmanager(lifespan)
            async with ctxmgr(**solved.values) as value:
                yield value

    return _solve_lifespan
