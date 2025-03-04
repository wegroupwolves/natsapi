from pydantic import BaseModel

from natsapi import NatsAPI, SubjectRouter
from natsapi.context import CTX_JSONRPC_ID
from natsapi.exceptions import JsonRPCException
from natsapi.models import JsonRPCReply, JsonRPCRequest


class StatusResult(BaseModel):
    status: str


class BrokerAlreadyExists(JsonRPCException):
    def __init__(self, data=None):
        self.code = -27001
        self.message = "BROKER_EXISTS"
        self.data = data


async def test_send_request_should_get_successful_reply(app):
    @app.request(subject="foo")
    async def _(app):
        return {"status": "OK"}

    reply = await app.nc.request("natsapi.development.foo", {"foo": 1})
    assert reply.result["status"] == "OK"


async def test_nonexistant_subject_should_get_failed_reply(app):
    reply = await app.nc.request("natsapi.development.nonexistant.CREATE", {})
    assert reply.error.message == "NO_SUCH_ENDPOINT"
    assert reply.error.code == -32601


async def test_incorrect_payload_should_get_failed_reply(app):
    @app.request(subject="foo")
    async def test(app, foo: int):
        return {"status": "OK", "foo": foo}

    reply = await app.nc.request("natsapi.development.foo", {"foo": "str"})
    assert reply.error.code == -40001


async def test_incorrect_request_format_should_fail(app):
    @app.request(subject="foo")
    async def test(app, foo: int, bar: str = None):
        return {"status": "OK", "foo": foo, "bar": bar}

    payload = {"timeout": 60, "foo": "str"}
    reply = await app.nc.request("natsapi.development.foo", payload)
    assert reply.error.code == -40001


async def test_payload_with_request_method_in_payload_should_find_endpoint(app):
    @app.request(subject="foo")
    async def test(app, foo: int):
        return {"status": "OK", "foo": foo}

    reply = await app.nc.request("natsapi.development.foo", {"foo": 1})
    assert reply.result["status"] == "OK"


async def test_payload_with_request_method_in_subject_and_payload_should_prioritize_subject(app):
    @app.request(subject="foo")
    async def _(app, foo: int):
        return {"status": "OK", "foo": foo}

    reply = await app.nc.request("natsapi.development.foo", {"foo": 1})
    assert reply.result["status"] == "OK"


async def test_no_such_endpoint(app):
    reply = await app.nc.request("natsapi.development.foo", {"foo": 1})
    assert reply.error.message == "NO_SUCH_ENDPOINT"
    assert reply.error.code == -32601


async def test_payload_with_empty_request_method_and_method__in_subject_get_successful_reply(app):
    @app.request(subject="foo")
    async def _(app, foo: int):
        return {"status": "OK", "foo": foo}

    reply = await app.nc.request("natsapi.development.foo", {"foo": 1})
    assert reply.result["status"] == "OK"


async def test_payload_with_empty_request_method_and_method__in_subject_get_successful_reply_with_return_model(app):
    @app.request(subject="foo")
    async def _(app, foo: int):
        return StatusResult(status="OK")

    reply = await app.nc.request("natsapi.development.foo", {"foo": 1})
    assert reply.result["status"] == "OK"


async def test_unhandled_application_error_should_get_failed_reply(app):
    expected = EOFError("Unhandled exception, e.g. UniqueViolationError")
    router = SubjectRouter()

    @router.request("error.CONVERT", result=BaseModel)
    def raise_exception(app):
        raise expected

    app.include_router(router)

    reply = await app.nc.request("natsapi.development.error.CONVERT", {})
    actual = reply.error.data

    assert type(expected).__name__ == actual["type"]
    assert reply.error.code == -40000


async def test_method_raised_domain_specific_error_should_get_failed_reply_in_domain_error_range(app):
    router = SubjectRouter()

    @router.request("error.CONVERT", result=BaseModel)
    def raise_exception(app):
        raise BrokerAlreadyExists("Broker with UUID already exists in DB")

    app.include_router(router)

    reply = await app.nc.request("natsapi.development.error.CONVERT", {})
    assert reply.error.message == "BROKER_EXISTS"
    assert reply.error.code == -27001


async def test_handle_request_meant_for_multiple_services_should_get_successful_reply(client_config, event_loop):
    # given
    app = NatsAPI("natsapi.development", client_config=client_config)

    router = SubjectRouter()

    @router.request(subject="bar")
    async def _(app):
        return {"status": "OK"}

    app.include_router(router, root_path="bar")

    await app.startup(loop=event_loop)

    # when
    reply = await app.nc.request("bar.bar", {})

    # then
    assert reply.result["status"] == "OK"

    # cleanup
    await app.shutdown(app)


async def test_skip_validation_should_pass_original_dict_in_validator_and_have_model_in_schema(app):
    class SomeParams(BaseModel):
        foo: str

    @app.request("skip_validation.CREATE", result=StatusResult, skip_validation=True)
    def _(app, data: SomeParams, **kwargs):
        kwargs = kwargs
        _ = data.get("foo")  # Should throw error if this is a pydantic model
        return {"status": str(type(data))}

    reply = await app.nc.request(
        "natsapi.development.skip_validation.CREATE",
        {"data": {"foo": "string", "undocumented_param": "bar"}, "extra_param": "string"},
    )
    assert "dict" in reply.result["status"]

    schema = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert "SomeParams" in schema["components"]["schemas"]


async def test_each_nats_request_should_have_different_id(app, natsapi_mock):
    # given:
    await natsapi_mock.request("foobar", response={"status": "OK"})

    # when: 2 reqeusts
    await app.nc.request("foobar", timeout=1)
    await app.nc.request("foobar", timeout=1)

    # then:
    assert natsapi_mock.payloads["foobar"][0]["id"] != natsapi_mock.payloads["foobar"][1]["id"]


async def test_send_request_should_store_jsonrpc_id_in_contextvars(app):
    @app.request(subject="foo")
    async def _(app):
        return {"jsonrpc_id": CTX_JSONRPC_ID.get()}

    json_rpc_payload = JsonRPCRequest(params={"foo": 1}, method=None, timeout=60)
    reply_raw = await app.nc.nats.request("natsapi.development.foo", json_rpc_payload.json().encode(), 60, headers=None)
    reply = JsonRPCReply.parse_raw(reply_raw.data)

    assert reply.result["jsonrpc_id"] == str(json_rpc_payload.id)
