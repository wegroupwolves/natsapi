from pydantic.main import BaseModel

from natsapi import NatsAPI
from natsapi.exceptions import JsonRPCException
from natsapi.models import JsonRPCError, JsonRPCRequest


async def test_overwrite_default_exception_should_use_custom_method(app):
    @app.exception_handler(JsonRPCException)
    def handle_custom_jsonrpc(exc: JsonRPCException, request: JsonRPCRequest, subject: str) -> JsonRPCError:
        return JsonRPCError(code=exc.code, message=exc.message)

    assert app._exception_handlers[JsonRPCException] == handle_custom_jsonrpc

    @app.request("test.RETRIEVE", result=BaseModel)
    def _(app: NatsAPI):
        raise JsonRPCException(code=42, message="hello world")

    reply = await app.nc.request("natsapi.development.test.RETRIEVE", {})
    assert reply.error.code == 42
    assert reply.error.message == "hello world"


async def test_add_custom_exception_should_use_handler_when_exception_is_thrown(app):
    class CustomException(Exception):
        def __init__(self, msg: str, rpc_code: int):
            self.rpc_code = rpc_code
            self.msg = msg

    @app.exception_handler(CustomException)
    async def handle_custom_exception(exc: CustomException, request: JsonRPCRequest, subject: str) -> JsonRPCError:
        return JsonRPCError(code=exc.rpc_code, message=exc.msg)

    assert app._exception_handlers[CustomException] == handle_custom_exception

    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        raise CustomException(rpc_code=500, msg="custom_message")

    reply = (await app.nc.request("natsapi.development.test.RETRIEVE", {})).error
    assert reply.code == 500
    assert reply.message == "custom_message"


async def test_throw_derived_custom_exception_should_use_base_exception_handler(app):
    class CustomException(Exception):
        def __init__(self, msg: str, rpc_code: int):
            self.rpc_code = rpc_code
            self.msg = msg

    class DerivedException(CustomException):
        def __init__(self, msg: str, rpc_code: int):
            super().__init__(msg, rpc_code)

    @app.exception_handler(CustomException)
    async def handle_custom_exception(exc: CustomException, request: JsonRPCRequest, subject: str) -> JsonRPCError:
        return JsonRPCError(code=exc.rpc_code, message=exc.msg)

    assert app._exception_handlers[CustomException] == handle_custom_exception

    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        raise DerivedException(rpc_code=500, msg="custom_message")

    reply = (await app.nc.request("natsapi.development.test.RETRIEVE", {})).error
    assert reply.code == 500
    assert reply.message == "custom_message"


async def test_default_jsonrpc_exception_handler_should_handle_exception_and_return_default_error_reply(app):
    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        raise JsonRPCException(code=500, message="custom_message")

    reply = (await app.nc.request("natsapi.development.test.RETRIEVE", {})).error

    assert reply.code == 500
    assert reply.message == "custom_message"
    assert reply.data
    assert reply.data["type"] == "JsonRPCException"
    assert reply.data["errors"] == []


async def test_default_validation_error_handler_should_handle_exception_and_return_default_error_reply(app):
    class TestClass(BaseModel):
        a: int
        b: str

    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        TestClass(a="abc")

    reply = (await app.nc.request("natsapi.development.test.RETRIEVE", {})).error

    assert reply.code == -40001
    assert reply.message
    assert reply.data
    assert reply.data["type"] == "ValidationError"
    assert reply.data["errors"] != []
    assert len(reply.data["errors"]) == 2

    for e in reply.data["errors"]:
        assert e["type"] == "ValidationError"
        assert e["target"]
        assert e["message"]


async def test_default_exception_handler_should_handle_exception_and_return_default_error_reply(app):
    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        raise Exception("Hello world")

    reply = (await app.nc.request("natsapi.development.test.RETRIEVE", {})).error

    assert reply.code == -40000
    assert reply.message == "Hello world"
    assert reply.data
    assert reply.data["type"] == "Exception"
    assert reply.data["errors"] == []


async def test_default_exception_handler_should_write_error_log(app, caplog):
    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        raise Exception("Hello world")

    await app.nc.request("natsapi.development.test.RETRIEVE", {})

    errors = [r for r in caplog.records if r.levelname in ["ERROR"]]
    assert len(errors) == 1
    assert "Hello world" in str(errors[0])


async def test_default_jsonrpc_exception_handler_should_write_warning_log(app, caplog):
    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        raise JsonRPCException(code=42, message="Hello world")

    await app.nc.request("natsapi.development.test.RETRIEVE", {})

    errors = [r for r in caplog.records if r.levelname in ["ERROR"]]
    assert len(errors) == 1
    assert "Hello world" in str(errors[0])


async def test_default_validation_error_handler_should_write_warning_log(app, caplog):
    class TestClass(BaseModel):
        a: int
        b: str

    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        TestClass(a="abc")

    await app.nc.request("natsapi.development.test.RETRIEVE", {})

    errors = [r for r in caplog.records if r.levelname in ["ERROR"]]
    assert len(errors) == 1
    assert "validation errors" in str(errors[0]), f"Expected validation error message, got: {str(errors[0])}"


async def test_default_exception_handler_should_handle_formatted_exception_and_return_default_error_reply(app):
    class FormattedException(Exception):
        def __init__(
            self,
            msg,
            domain=None,
            detail=None,
            code=None,
            rpc_code=None,
        ):
            self.msg = msg
            self.domain = (domain,)
            self.detail = detail
            self.code = code
            self.rpc_code = rpc_code

    @app.request("test.RETRIEVE", result=BaseModel)
    async def _(app: NatsAPI):
        raise FormattedException(
            msg="NATS_ERROR",
            detail="Something went wrong while working with NATS.",
            domain="Some service",
            code=500,
            rpc_code=-27000,
        )

    reply = (await app.nc.request("natsapi.development.test.RETRIEVE", {})).error

    assert reply.code == -27000
    assert reply.message == "NATS_ERROR: Something went wrong while working with NATS."
    assert reply.data
    assert reply.data["type"] == "FormattedException"
    assert reply.data["errors"] == []
