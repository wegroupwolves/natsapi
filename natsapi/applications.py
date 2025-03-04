import asyncio
import inspect
import signal
from collections.abc import Callable
from typing import Any, Optional, Union

from pydantic import BaseModel, ValidationError

from natsapi.asyncapi import Errors, ExternalDocumentation
from natsapi.asyncapi.models import AsyncAPI
from natsapi.asyncapi.utils import get_asyncapi
from natsapi.client import Config, NatsClient
from natsapi.client.config import default_config
from natsapi.exception_handlers import handle_internal_error, handle_jsonrpc_exception, handle_validation_error
from natsapi.exceptions import DuplicateRouteException, JsonRPCException
from natsapi.logger import logger
from natsapi.routing import Pub, Publish, Request, Sub, SubjectRouter
from natsapi.state import State
from natsapi.types import DecoratedCallable


class NatsAPI:
    def __init__(
        self,
        root_path: str,
        *,
        app: Any = None,
        client_config: Optional[Config] = None,
        rpc_methods: Optional[list[str]] = None,
        exception_handlers: Optional[dict[type[Exception], Callable[[type[Exception]], JsonRPCException]]] = None,
        title: str = "NatsAPI",
        version: str = "0.1.0",
        description: str = None,
        tags: Optional[list[dict[str, Any]]] = None,
        servers: Optional[dict[str, Union[str, Any]]] = None,
        domain_errors: Optional[dict[str, Any]] = None,
        external_docs: Optional[dict[str, Any]] = None,
    ):
        """
        Parameters
        ----------
        root_path: str The path that every application-specific subject
        app: FastAPI Must be a FastAPI instance or None. If none the app is the NatsAPI instance itself
        """
        self.routes: dict[str, Request] = {}
        self.root_path = root_path
        self._root_paths = [root_path]
        self.rpc_methods = rpc_methods if rpc_methods else None
        self.title = title
        self.version = version
        self.description = description
        self.asyncapi_servers = servers or {}
        self.asyncapi_external_docs = external_docs
        self.asyncapi_tags = tags or []
        self.asyncapi_version = "2.0.0"
        self.domain_errors: Errors = domain_errors
        self.asyncapi_schema: Optional[dict[str, Any]] = None
        self.nc: NatsClient = None
        self.subs: set[Sub] = set()
        self.pubs: set[Pub] = set()
        self.state = State()
        self._on_startup_method = None
        self._on_shutdown_method = None
        self.client_config = client_config or default_config
        self._exception_handlers: dict[type[Exception], Callable[[type[Exception]], JsonRPCException]] = (
            {} if exception_handlers is None else dict(exception_handlers)
        )
        self._exception_handlers.setdefault(JsonRPCException, handle_jsonrpc_exception)
        self._exception_handlers.setdefault(ValidationError, handle_validation_error)
        self._exception_handlers.setdefault(Exception, handle_internal_error)
        try:
            self.loop = asyncio.get_running_loop()
            self._sharing_loop = True
        except RuntimeError:
            self.loop = asyncio.get_event_loop()
            self._sharing_loop = False

        if app is not None:
            app_type = str(type(app))
            assert (
                "FastAPI" in app_type or "Sanic" in app_type
            ), f"App must be a FastAPI or Sanic instance, got {app_type}"
            self.app = app
        else:
            self.app = self

    async def __aenter__(self):
        await self.startup(self.loop)
        return self

    async def __aexit__(self, *args):
        await self.shutdown()

    def include_router(self, router: type[SubjectRouter], root_path: str = None) -> None:
        current_root_path = root_path or self.root_path
        if current_root_path not in self._root_paths:
            self._root_paths.append(current_root_path)

        for subject in router.routes:
            if self.rpc_methods:
                method = subject.subject.split(".")[-1]
                assert (
                    method in self.rpc_methods
                ), f"'{method}' is an invalid request method for handler {subject.endpoint.__name__}. Allowed methods: {self.rpc_methods}"
            key_name = ".".join([current_root_path, subject.subject])
            if key_name in self.routes:
                raise DuplicateRouteException(f"{key_name} is defined twice!")

            self.routes[key_name] = subject

        self.subs = self.subs | router.subs
        self.pubs = self.pubs | router.pubs

    def generate_asyncapi(self) -> dict[str, Any]:
        if not self.asyncapi_schema:
            self.asyncapi_schema = get_asyncapi(
                title=self.title,
                version=self.version,
                asyncapi_version=self.asyncapi_version,
                description=self.description,
                routes=self.routes,
                subs=self.subs,
                pubs=self.pubs,
                errors=self.domain_errors,
                servers=self.asyncapi_servers,
                external_docs=self.asyncapi_external_docs,
            )
        return self.asyncapi_schema

    def _add_asyncapi_route(self) -> dict[str, Any]:
        """
        Adds default route to retrieve the asyncapi schema.
        """

        @self.request("schema.RETRIEVE", result=AsyncAPI, include_schema=False)
        def retrieve_asyncapi_schema(app):
            return self.generate_asyncapi()

    def on_startup(self, method: Callable) -> Callable[[DecoratedCallable], DecoratedCallable]:
        self._on_startup_method = method

    def on_shutdown(self, method: Callable) -> Callable[[DecoratedCallable], DecoratedCallable]:
        self._on_shutdown_method = method

    async def startup(self, loop=None):
        if loop:
            self.loop = loop
            self._sharing_loop = True
        else:
            self._listen_to_signals()

        self.nc = NatsClient(
            self.routes,
            app=self.app,
            config=self.client_config,
            exception_handlers=self._exception_handlers,
        )
        await self.nc.connect()
        logger.info("Connected to NATS server")

        if self._on_startup_method:
            if inspect.iscoroutinefunction(self._on_startup_method):
                await self._on_startup_method()
            else:
                self._on_startup_method()

        for path in self._root_paths:
            sub_path = ".".join([path, ">"])
            await self.nc.root_path_subscribe(
                sub_path,
                cb=self.nc.handle_request,
                queue=self.client_config.subscribe.queue,
            )
            self.include_subs(
                [
                    Sub(
                        sub_path,
                        queue=self.client_config.subscribe.queue,
                        summary=f"Sub to root path {sub_path}",
                        tags=["automatic subs"],
                    ),
                ],
            )
            logger.info(f"Subscribed to {sub_path}")
        self._add_asyncapi_route()
        logger.info(f"Asyncapi schema can be found on {self.root_path}.schema.RETRIEVE")

        return self

    def _listen_to_signals(self):
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            self.loop.add_signal_handler(s, lambda s=s: asyncio.create_task(self.shutdown(signal=s)))

    async def shutdown(self, signal=None):
        if signal:
            logger.info("Received kill signal")

        logger.warning("Cleanup coroutines that handle NATS messages.")
        cleanup = [x for x in asyncio.all_tasks() if x.get_name().startswith("natsapi_")]
        await asyncio.gather(*cleanup, return_exceptions=True)
        logger.warning(f"Cleaned up {len(cleanup)} coroutines.")

        await self.nc.shutdown()

        if self._on_shutdown_method:
            logger.info("Invoking shutdown of application instance.")
            if inspect.iscoroutinefunction(self._on_shutdown_method):
                await self._on_shutdown_method()
            else:
                self._on_shutdown_method()
            logger.info("Shutdown of application instance completed.")

        if not self._sharing_loop:
            logger.info("Self-managed loop: cancelling remaining asyncio tasks.")
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            [task.cancel() for task in tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Finished cancelling tasks, results: {results}")
            self.loop.stop()

    def run(self):
        self.loop.run_until_complete(self.startup())
        self.loop.run_forever()

    def add_request(
        self,
        subject: str,
        endpoint: Callable[..., Any],
        *,
        result=type[Any],
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        suggested_timeout: Optional[float] = None,
        include_schema: Optional[bool] = True,
    ) -> None:
        request = Request(
            subject=subject,
            endpoint=endpoint,
            result=result,
            skip_validation=skip_validation,
            description=description,
            deprecated=deprecated,
            tags=tags,
            summary=summary,
            suggested_timeout=suggested_timeout,
            include_schema=include_schema,
        )
        if self.rpc_methods:
            method = subject.split(".")[-1]
            assert (
                method in self.rpc_methods
            ), f"'{method}' is an invalid request method in handler '{endpoint.__name__}'. Allowed methods: {self.rpc_methods}"

        key_name = ".".join([self.root_path, request.subject])
        if key_name in self.routes:
            raise DuplicateRouteException(f"{key_name} is defined twice!")
        self.routes[key_name] = request

    def add_publish(
        self,
        subject: str,
        endpoint: Callable[..., Any],
        *,
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        include_schema: Optional[bool] = True,
    ) -> None:
        publish = Publish(
            subject=subject,
            endpoint=endpoint,
            skip_validation=skip_validation,
            description=description,
            deprecated=deprecated,
            tags=tags,
            summary=summary,
            include_schema=include_schema,
        )
        if self.rpc_methods:
            method = subject.split(".")[-1]
            assert (
                method in self.rpc_methods
            ), f"'{method}' is an invalid request method in handler '{endpoint.__name__}'. Allowed methods: {self.rpc_methods}"

        key_name = ".".join([self.root_path, publish.subject])
        if key_name in self.routes:
            raise DuplicateRouteException(f"{key_name} is defined twice!")
        self.routes[key_name] = publish

    def request(
        self,
        subject: str,
        *,
        result=type[Any],
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        suggested_timeout: Optional[float] = None,
        include_schema: Optional[bool] = True,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_request(
                subject=subject,
                endpoint=func,
                result=result,
                skip_validation=skip_validation,
                description=description,
                deprecated=deprecated,
                tags=tags,
                summary=summary,
                suggested_timeout=suggested_timeout,
                include_schema=include_schema,
            )
            return func

        return decorator

    def publish(
        self,
        subject: str,
        *,
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        include_schema: Optional[bool] = True,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_publish(
                subject=subject,
                endpoint=func,
                skip_validation=skip_validation,
                description=description,
                deprecated=deprecated,
                tags=tags,
                summary=summary,
                include_schema=include_schema,
            )
            return func

        return decorator

    def add_pub(
        self,
        subject: str,
        params: BaseModel,
        *,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ) -> None:
        """
        Include pub in asyncapi schema
        """
        pub = Pub(
            subject,
            params,
            summary=summary,
            description=description,
            tags=tags or None,
            externalDocs=externalDocs,
        )
        self.pubs.add(pub)

    def pub(
        self,
        subject: str,
        *,
        params=type[Any],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_pub(
                subject=subject,
                params=params,
                summary=summary,
                description=description,
                tags=tags,
                externalDocs=externalDocs,
            )
            return func

        return decorator

    def include_subs(self, subs: list[Sub]):
        for sub in subs:
            self.subs.add(sub)

    def add_sub(
        self,
        subject: str,
        *,
        queue: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ) -> None:
        """
        Include sub in asyncapi schema
        """
        sub = Sub(
            subject,
            queue=queue,
            summary=summary,
            description=description,
            tags=tags or None,
            externalDocs=externalDocs,
        )
        self.subs.add(sub)

    def sub(
        self,
        subject: str,
        *,
        queue: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_sub(
                subject=subject,
                queue=queue,
                summary=summary,
                description=description,
                tags=tags,
                externalDocs=externalDocs,
            )
            return func

        return decorator

    def include_pubs(self, pubs: list[Pub]):
        for pub in pubs:
            self.pubs.add(pub)

    def add_exception_handler(
        self,
        exc_class: type[Exception],
        handler: Callable[[Exception], JsonRPCException],
    ) -> None:
        self._exception_handlers[exc_class] = handler

    def exception_handler(self, exc_class: type[Exception]) -> Callable:
        def decorator(func: Callable[[Exception], JsonRPCException]) -> Callable:
            self.add_exception_handler(exc_class, func)
            return func

        return decorator
