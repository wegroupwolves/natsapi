import asyncio

import pytest
from pydantic import BaseModel

from natsapi import NatsAPI


class FastAPI(BaseModel):
    pass


@pytest.mark.skip(reason="Removed fastapi dependency.")
async def test_run_natsapi_on_same_loop_should_run_simultaneously():
    fastapi = FastAPI()
    natsapi = NatsAPI("natsapi.dev")
    app = NatsAPI("test")
    await app.startup()

    @fastapi.on_event("startup")
    async def setup():
        loop = asyncio.get_running_loop()
        await natsapi.startup(loop=loop)

    @fastapi.on_event("shutdown")
    async def teardown():
        await natsapi.shutdown()


@pytest.mark.skip(reason="Removed fastapi dependency.")
def test_pass_fastapi_instance_as_app_should_work():
    fastapi = FastAPI()

    fastapi.state.db = "postgresql"
    fastapi.controllers = "dirty_object"

    natsapi = NatsAPI("natsapi.development", app=fastapi)

    assert type(natsapi.app) is type(fastapi)
    assert natsapi.app.controllers == "dirty_object"
    assert natsapi.app.state.db == "postgresql"
