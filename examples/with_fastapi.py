import asyncio
import logging

from fastapi import FastAPI

from natsapi import NatsAPI

logging.basicConfig(level=logging.INFO)

fastapi = FastAPI()
natsapi = NatsAPI("natsapi.dev")


@fastapi.on_event("startup")
async def setup():
    loop = asyncio.get_running_loop()
    await natsapi.startup(loop=loop)

    logging.info("Connect to db")


@fastapi.on_event("shutdown")
async def teardown():
    await natsapi.shutdown()

    logging.info("Disconnect from db")


# uvicorn example.with_fastapi:fastapi
