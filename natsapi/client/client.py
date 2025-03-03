import asyncio
import inspect
import json
import logging
import secrets
from collections.abc import Callable
from ssl import create_default_context
from typing import Any, Optional
from uuid import uuid4

from nats.aio.client import Client as NATS

from natsapi.context import CTX_JSONRPC_ID
from natsapi.exceptions import JsonRPCException, JsonRPCUnknownMethodException
from natsapi.models import JsonRPCError, JsonRPCReply, JsonRPCRequest
from natsapi.routing import Request

from .config import Config, default_config


class NatsClient:
    def __init__(
        self,
        routes: dict[str, Request],
        app: Any = None,
        config: Optional[Config] = None,
        exception_handlers: Optional[dict[type[Exception], Callable[[type[Exception]], JsonRPCException]]] = None,
    ) -> None:
        self.routes = routes
        self.app = app
        self.config = config or default_config
        self._exception_handlers = exception_handlers
        self.nats = NATS()

    async def connect(self) -> None:
        cfg = self.config.connect
        cfg.error_cb = cfg.error_cb or self._error_cb
        cfg.closed_cb = cfg.closed_cb or self._closed_cb
        cfg.reconnected_cb = cfg.reconnected_cb or self._reconnected_cb
        cfg.tls = cfg.tls or create_default_context()

        await self.nats.connect(**(cfg.dict()))

    async def root_path_subscribe(self, subject: str, cb: Callable, queue: str = ""):
        await self.nats.subscribe(subject, cb=cb, **(self.config.subscribe.dict()))

    async def publish(self, subject: str, params: dict[str, Any], method: str = None, reply=None, headers: dict = None):
        """
        method: legacy attribute, used for backwards compatibility
        """
        json_rpc_payload = JsonRPCRequest(id=uuid4(), params=params, method=method, timeout=-1)
        await self.nats.publish(subject, json_rpc_payload.json().encode(), reply=reply, headers=headers)

    async def publish_on_reply(self, subject, payload):
        await self.nats.publish(subject, payload)

    async def request(
        self,
        subject: str,
        params: dict[str, Any] = dict(),
        timeout=60,
        method: str = None,
        headers: dict = None,
    ) -> JsonRPCReply:
        """
        method: legacy attribute, used for backwards compatibility
        """
        json_rpc_payload = JsonRPCRequest(params=params, method=method, timeout=timeout)
        reply_raw = await self.nats.request(subject, json_rpc_payload.json().encode(), timeout, headers=headers)
        reply = JsonRPCReply.parse_raw(reply_raw.data)
        return reply

    async def handle_request(self, msg):
        if msg.reply and msg.reply != "None":
            asyncio.create_task(self._handle_request(msg), name="natsapi_" + secrets.token_hex(16))
        else:
            asyncio.create_task(self._handle_publish(msg), name="natsapi_" + secrets.token_hex(16))

    async def _handle_publish(self, msg):
        request = JsonRPCRequest.parse_raw(msg.data)
        request.id = request.id or uuid4()

        subject = msg.subject

        if subject not in self.routes and request.method:
            subject = ".".join([subject, request.method])

        try:
            logging.debug(f"Handling: {subject}")
            route: Request = self.routes[subject]
        except KeyError as e:
            raise JsonRPCUnknownMethodException(data=f"No such endpoint available for {subject}") from e

        handler = route.endpoint
        params_model = route.params
        params = request.params if route.skip_validation else vars(params_model.parse_obj(request.params))

        if inspect.iscoroutinefunction(handler):
            await handler(app=self.app, **params)
        else:
            handler(self.app, **params)

    async def _handle_request(self, msg):
        request = result = None
        try:
            request = JsonRPCRequest.parse_raw(msg.data)
            request.id = request.id or uuid4()

            CTX_JSONRPC_ID.set(request.id)
            subject = msg.subject

            if subject not in self.routes and request.method:
                subject = ".".join([subject, request.method])

            try:
                logging.debug(f"Handling: {subject}")
                route: Request = self.routes[subject]
            except KeyError as e:
                raise JsonRPCUnknownMethodException(data=f"No such endpoint available. Checked for {subject}") from e

            handler = route.endpoint
            params_model = route.params
            params = request.params if route.skip_validation else vars(params_model.parse_obj(request.params))

            if inspect.iscoroutinefunction(handler):
                result = await handler(app=self.app, **params)
            else:
                result = handler(self.app, **params)

            if not isinstance(result, dict):
                if hasattr(result, "dict"):
                    result = result.dict()
                elif hasattr(result, "json"):
                    result = json.loads(result.json())

            reply = JsonRPCReply(id=request.id, result=result)
        except Exception as exc:
            if not request:
                request = JsonRPCRequest(params={}, timeout=60)
            exception_handler = self._lookup_exception_handler(exc)
            if inspect.iscoroutinefunction(exception_handler):
                error: JsonRPCError = await exception_handler(exc, request, msg.subject)
            else:
                error: JsonRPCError = exception_handler(exc, request, msg.subject)
            reply = JsonRPCReply(id=request.id, error=error)
        finally:
            await self.publish_on_reply(msg.reply, reply.json().encode())

    def _lookup_exception_handler(self, exc: Exception) -> Optional[Callable]:
        """
        Gets list of all the types the exception instance inherits from and checks if
        exception type is in the 'exception_handlers' dict.

        e.g. your handler throws a BrokerNotFoundException, the generated list will be:
        [BrokerNotFoundException, FormattedException, Exception, BaseException]

        If you have written an handler for FormattedException, this method will return that handler.
        Worst-case is getting the default handler for Exception

        The method will only return 'None' if you have a custom exception inheriting from BaseException.
        But inheriting from BaseException is bad practice, and your application should crash if you do this.
        """
        for cls in type(exc).__mro__:
            if cls in self._exception_handlers:
                return self._exception_handlers[cls]
        return None

    async def _error_cb(self, e):
        logging.exception(e)

    async def _closed_cb(self):
        logging.warning("NATS CLOSED")

    async def _reconnected_cb(self):
        logging.warning(f"Got reconnected to {self.nats.connected_url.netloc}")

    async def shutdown(self, signal=None):
        await self.nats.drain()
        logging.info("All NATS connections put in drain state.")
        await self.nats.close()
        logging.info("All NATS connections closed.")
