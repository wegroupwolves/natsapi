import asyncio
import os

import pytest

from natsapi import NatsAPI
from natsapi.client import Config
from natsapi.client.config import ConnectConfig


@pytest.fixture(scope="session")
def client_config():
    connect = ConnectConfig(
        servers=os.environ.get("HOST_NATS", "nats://127.0.0.1:4222"),
        nkeys_seed=os.environ.get("NATS_CREDENTIALS_FILE", None),
    )
    return Config(connect=connect)


@pytest.fixture(scope="function")
async def app(client_config, event_loop):
    """
    Clean NatsAPI instance with rootpath
    """
    app = NatsAPI("natsapi.development", client_config=client_config)
    await app.startup(loop=event_loop)
    yield app
    await app.shutdown(app)


@pytest.fixture(scope="session")
def event_loop():
    yield asyncio.get_event_loop()
