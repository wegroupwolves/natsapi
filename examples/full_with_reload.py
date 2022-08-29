import logging

from pydantic import BaseModel

from natsapi import NatsAPI
from natsapi.models import JsonRPCError, JsonRPCRequest

logging.basicConfig(level=logging.INFO)


class StatusResult(BaseModel):
    status: str


app = NatsAPI("natsapi.development")


@app.on_startup
async def setup():
    logging.info("[STARTUP]")


@app.on_shutdown
async def teardown():
    logging.info("[TEARDOWN]")


@app.publish("foo.do", description="This is the description of the publish request")
async def _(app, bar: int):
    bar = bar
    logging.info("Publish called!")


@app.request("healthz.get", description="Is the server still up?", result=StatusResult)
async def _(app: NatsAPI):
    return {"status": "OK"}


@app.exception_handler(Exception)
async def handle_exception_custom(exc: Exception, request: JsonRPCRequest, subject: str) -> JsonRPCError:
    return JsonRPCError(code=-90001, message="VALIDATION_ERROR", data={"error_str": str(exc)})


if __name__ == "__main__":
    app.run(reload=False)
