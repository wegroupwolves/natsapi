import pytest
from pydantic import BaseModel

from natsapi import NatsAPI, Pub, Sub, SubjectRouter


class NotificationParams(BaseModel):
    notification: str
    service: str


class StatusResult(BaseModel):
    status: str


class ThemeCreateCmd(BaseModel):
    name: str


async def test_minimal_app_should_have_route_with_minimal_schema(app):
    themes_router = SubjectRouter()

    @themes_router.request("themes.CREATE", result=StatusResult)
    def create_theme(app, data: ThemeCreateCmd):
        return {"status": "OK"}

    app.include_router(themes_router)

    reply = await app.nc.request("natsapi.development.themes.CREATE", {"data": {"name": "orange"}})

    assert reply.result["status"] == "OK"


async def test_async_startup_should_run_with_setup_method(client_config, event_loop):
    app = NatsAPI("natsapi.development", client_config=client_config)

    @app.on_startup
    async def setup():
        db = "connected"
        assert db == "connected"

    await app.startup(loop=event_loop)
    await app.shutdown()


async def test_async_shutdown(client_config, event_loop):
    app = NatsAPI("natsapi.development", client_config=client_config)

    @app.on_shutdown
    async def teardown():
        db = "disconnected"
        assert db == "disconnected"

    await app.startup(loop=event_loop)
    await app.shutdown()


def test_pass_unrecognized_type_for_app_attr_should_fail(app):
    with pytest.raises(AssertionError):
        _ = NatsAPI("natsapi.development", app=42)


def test_app_request_decorator_should_add_request_to_routes():
    app = NatsAPI("natsapi.development")

    @app.request("request_without_router", result=StatusResult)
    def new_route(app):
        return {"status": "OK"}

    assert len(app.routes) == 1
    assert app.routes["natsapi.development.request_without_router"]
    assert app.routes["natsapi.development.request_without_router"].subject == "request_without_router"


def test_subs_to_root_paths_should_be_documented(app: NatsAPI):
    app.include_subs([Sub("*.subject.>", queue="natsapi")])
    assert len(app.subs) == 2


def test_include_pub_should_add_pub_to_app(app: NatsAPI):
    app.include_pubs([Pub("some.subject", NotificationParams)])
    assert len(app.pubs) == 1


def test_add_pub_should_add_pub_to_app(app: NatsAPI):
    @app.pub("notifications.CREATE", params=NotificationParams)
    @app.request("subject.RETRIEVE", result=StatusResult)
    async def _(app: NatsAPI):
        await app.nc.publish("notifications.CREATE", {"notification": "Hi", "service": "SMT"})
        return {"status": "OK"}

    assert len(app.pubs) == 1


def test_add_sub_should_add_sub_to_app(app: NatsAPI):
    @app.sub("*.subject.>", queue="natsapi")
    @app.request("subject.RETRIEVE", result=StatusResult)
    async def handle_request_with_sub(app: NatsAPI):
        await app.nc.subscribe("*.subject.>", queue="natsapi", cb=lambda _: print("some callback"))
        return {"status": "OK"}

    assert len(app.subs) == 2


def test_add_subject_that_doesnt_end_in_rpc_method_should_fail():
    JSON_RPC_METHODS = ["CREATE", "RETRIEVE", "UPDATE", "DELETE", "CONVERT", "EXPORT", "CALCULATE", "VERIFY"]
    app = NatsAPI("natsapi.development", rpc_methods=JSON_RPC_METHODS)

    with pytest.raises(AssertionError) as exc:

        @app.request("subject.UNKNOWN_RPC_METHOD", result=BaseModel)
        def handle_request(app):
            return {"Status": "OK"}

    assert str(JSON_RPC_METHODS) in str(exc)
    assert "invalid request method" in str(exc)


async def test_with_method_should_run_commands_within_with_block_and_shutdown_afterwards(client_config):
    async with NatsAPI("with_block", client_config=client_config) as app:
        reply = await app.nc.request("with_block.schema.RETRIEVE")
        assert reply.result


async def test_send_a_pub_should_send_without_error(app):
    await app.nc.publish("natsapi.development.test.CREATE", {})
