import asyncio
import json
import os
from collections import defaultdict
from typing import Any
from uuid import uuid4

import pytest
from nats.aio.client import Client as NATS
from nats.aio.client import Msg

from natsapi.exceptions import JsonRPCUnknownMethodException
from natsapi.models import JsonRPCReply


class NatsapiMock:
    """
    A simple, yet powerful utility to mock nats requests.
    define subject with response and error fakes, and NatsMock
    will give you the possibility to assert against payloads provided
    and the fakes that were given.

    A mock that can be used as follows:

    ```
    async def test(natsapi_mock):
        await natsapi_mock.request("<subject>", response={"foo": "bar"})

        reply = await nats.request("<subject>", {"id": 1}, timeout=1)

        # use the fakes in your app
        assert reply.result == {"foo": "bar"}

        # test against the payload provided in the nats request
        assert nats_service_mock.payloads["<subject>"][0]["params"]["id"] == 1
    ```
    """

    def __init__(self, host: str) -> None:
        self.host = host
        self.nats: NATS = NATS()
        self.subjects: dict[str, tuple[Any, Any]] = {}
        self.responses: dict[str, tuple[Any, Any]] = {}
        self.payloads: dict[str, Any] = defaultdict(list)

    async def lifespan(self) -> None:
        await self.nats.connect(self.host, verbose=True, ping_interval=5)

    async def wait_startup(self):
        counter = 0
        while self.nats.is_connected is False:
            await asyncio.sleep(0.1)
            counter += 1
            if counter == 10:
                raise Exception("Waited to long for nats to connect!")

    async def handle(self, message: Msg) -> None:
        payload = json.loads(message.data.decode("utf-8"))

        try:
            result, error = self.responses[message.subject]

            if not isinstance(result, dict):
                if hasattr(result, "dict"):
                    result = result.dict()
                elif hasattr(result, "json"):
                    result = json.loads(result.json())

            response = JsonRPCReply(jsonrpc="2.0", id=uuid4(), error=error, result=result)
        except KeyError:
            exc = JsonRPCUnknownMethodException()
            response = JsonRPCReply(jsonrpc="2.0", id=uuid4(), error={"code": -1, "message": str(exc.message)})
        except Exception as e:
            response = JsonRPCReply(jsonrpc="2.0", id=uuid4(), error={"code": -1, "message": f"{type(e)}: {str(e)}"})
        finally:
            if message.subject not in self.payloads:
                self.payloads[message.subject] = []
            self.payloads[message.subject].append(payload)

        if message.reply:
            await self.nats.publish(message.reply, response.json().encode())

    async def request(self, subject: str, *, response: Any = None, error: dict[str, Any] = None) -> None:
        assert response or error, "Need a response of an error"
        self.responses[subject] = response, error
        await self.nats.subscribe(subject, cb=self.handle)
        await self.nats.flush(timeout=5)

    async def publish(self, subject: str) -> None:
        await self.nats.subscribe(subject, cb=self.handle)
        await self.nats.flush(timeout=5)

    async def __aenter__(self):
        await self.lifespan()
        await self.wait_startup()
        return self

    async def __aexit__(self, *args):
        await self.nats.drain()
        await self.nats.close()


@pytest.fixture
async def natsapi_mock() -> NatsapiMock:
    host = os.environ.get("HOST_NATS", "nats://127.0.0.1:4222")
    async with NatsapiMock(host=host) as mock:
        yield mock
