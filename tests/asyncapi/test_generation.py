from typing import Any, Union
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field

from natsapi import NatsAPI, Pub, SubjectRouter
from natsapi.asyncapi import Errors
from natsapi.asyncapi.models import ExternalDocumentation, Server
from natsapi.exceptions import JsonRPCException

pytestmark = pytest.mark.asyncio

production_server = Server(
    **{
        "url": "nats://127.0.0.1:{port}",
        "description": "Production NATS",
        "protocol": "nats",
        "protocolVersion": "2.0",
        "variables": {"port": {"default": "422"}},
    },
)

staging_server = Server(
    **{
        "url": "nats://127.0.0.1:{port}",
        "description": "Staging NATS",
        "protocol": "nats",
        "protocolVersion": "2.0",
        "variables": {"port": {"default": "422"}},
    },
)

servers_schema = {"production": production_server, "staging": staging_server}


class Pagination(BaseModel):
    page: int
    pagelen: int


class CreateResult(BaseModel):
    id: Any
    pagination: Pagination


class BrokerAlreadyExists(JsonRPCException):
    def __init__(self, data=None):
        self.code = -27001
        self.message = "BROKER_EXISTS"
        self.data = data


class SignatureException(JsonRPCException):
    def __init__(self, data=None) -> None:
        self.code = -27002
        self.message = "SIGNATURE_ERROR"
        self.data = data


domain_errors = Errors(lower_bound=-27000, upper_bound=-3000, errors=[BrokerAlreadyExists, SignatureException])

external_docs = ExternalDocumentation(
    description="This client uses the JsonRPC standard for the payloads. Requests follow the company guidelines.",
    url="https://github.com/wegroupwolves",
)


def test_generate_minimal_asyncapi_schema_should_generate():
    client = NatsAPI("natsapi.development")
    client.generate_asyncapi()
    schema = client.asyncapi_schema
    assert schema["asyncapi"] == "2.0.0"
    assert schema["defaultContentType"] == "application/json"
    assert schema["info"]["title"] == "NatsAPI"
    assert schema["info"]["version"] == "0.1.0"


def test_asyncapi_schema_generation_should_be_cached(monkeypatch):
    client = NatsAPI("natsapi.development")
    assert client.asyncapi_schema is None

    client.generate_asyncapi()
    s1 = client.asyncapi_schema
    assert s1 is not None

    # WHEN generating schema again
    def patched():
        return "Invalid schema"

    monkeypatch.setattr("natsapi.asyncapi.utils.get_asyncapi.__code__", patched.__code__)

    client.generate_asyncapi()
    s2 = client.asyncapi_schema
    assert id(s2) == id(s1)


def test_asyncapi_schema_w_personal_title_should_generate():
    client = NatsAPI(
        "natsapi.development",
        title="My Nats Client",
        description="This is my nats client",
        version="2.4.3",
    )
    client.generate_asyncapi()
    schema = client.asyncapi_schema
    assert schema["info"]["title"] == "My Nats Client"
    assert schema["info"]["description"] == "This is my nats client"
    assert schema["info"]["version"] == "2.4.3"


def test_generate_schema_w_servers_should_generate():
    client = NatsAPI("natsapi.development", servers=servers_schema)
    client.generate_asyncapi()
    schema = client.asyncapi_schema

    assert len(schema["servers"]) == len(servers_schema)
    assert schema["servers"]["production"] == servers_schema["production"].dict(exclude_none=True)
    assert schema["servers"]["staging"] == servers_schema["staging"].dict(exclude_none=True)


def test_generate_schema_w_external_docs_should_generate():
    client = NatsAPI("natsapi.development", external_docs=external_docs)
    client.generate_asyncapi()
    schema = client.asyncapi_schema
    assert schema["externalDocs"] == external_docs.dict()


async def test_generate_shema_w_requests_should_generate(app: NatsAPI):
    class BaseUser(BaseModel):
        email: str = Field(..., description="Unique email of user", example="foo@bar.com")
        password: str = Field(..., description="Password of user", example="Supers3cret")

    user_router = SubjectRouter(prefix="v1", tags=["users"], deprecated=True)

    @user_router.request(
        "users.CREATE",
        result=CreateResult,
        description="Creates user that can be used throughout the app",
        tags=["auth"],
        suggested_timeout=0.5,
    )
    def create_base_user(app):
        return {"id": uuid4()}

    app.include_router(user_router)
    app.generate_asyncapi()
    schema = app.asyncapi_schema
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["request"]["x-suggested-timeout"]
    assert (
        schema["channels"]["natsapi.development.v1.users.CREATE"]["request"]["operationId"]
        == "create_base_user_v1_users_CREATE"
    )
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["request"]["summary"]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["request"]["description"]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["request"]["tags"] == [
        {"name": "users"},
        {"name": "auth"},
    ]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["request"]["message"]["payload"]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["request"]["replies"]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["deprecated"]

    schema_from_request = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert schema_from_request == schema


async def test_generate_shema_w_publishes_should_generate(app: NatsAPI):
    class BaseUser(BaseModel):
        email: str = Field(..., description="Unique email of user", example="foo@bar.com")
        password: str = Field(..., description="Password of user", example="Supers3cret")

    user_router = SubjectRouter(prefix="v1", tags=["users"], deprecated=True)

    @user_router.publish(
        "users.CREATE",
        description="Creates user that can be used throughout the app",
        tags=["auth"],
    )
    def create_base_user(app):
        return {"id": uuid4()}

    app.include_router(user_router)
    app.generate_asyncapi()
    schema = app.asyncapi_schema
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["publish"]
    assert (
        schema["channels"]["natsapi.development.v1.users.CREATE"]["publish"]["operationId"]
        == "create_base_user_v1_users_CREATE"
    )
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["publish"]["summary"]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["publish"]["description"]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["publish"]["tags"] == [
        {"name": "users"},
        {"name": "auth"},
    ]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["publish"]["message"]["payload"]
    assert schema["channels"]["natsapi.development.v1.users.CREATE"]["publish"]

    schema_from_request = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert schema_from_request == schema


def test_dont_include_in_schema_should_generate():
    router = SubjectRouter()

    @router.request("not_included_router", result=BaseModel, include_schema=False)
    def test_not_included_subject():
        pass

    client = NatsAPI("natsapi.development")
    client.include_router(router)
    client.generate_asyncapi()
    schema = client.asyncapi_schema
    assert "channels" not in schema


def test_generate_domain_errors_schema_should_generate():
    app = NatsAPI("natsapi", domain_errors=domain_errors)

    app.generate_asyncapi()
    assert app.asyncapi_schema["errors"]["range"]["upper"] == domain_errors.dict()["upper_bound"]
    assert app.asyncapi_schema["errors"]["range"]["lower"] == domain_errors.dict()["lower_bound"]
    assert len(app.asyncapi_schema["errors"]["items"]) == len(domain_errors.dict()["errors"])


def test_root_subs_in_schema_should_be_in_schema(app: NatsAPI):
    app.generate_asyncapi()
    root_path_sub = app.asyncapi_schema["channels"]["natsapi.development.>"]
    assert root_path_sub["subscribe"]["summary"]


async def test_included_pub_in_schema_should_be_in_schema(app: NatsAPI):
    app.include_pubs([Pub("some.subject", Server)])

    assert len(app.pubs) == 1

    schema = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert schema["channels"]["some.subject"]
    assert schema["components"]["schemas"]["Server"]


def test_routes_use_identically_named_class_in_different_modules_should_reference_correctly():
    app = NatsAPI("natsapi.development")

    class SomeClassA(BaseModel):
        foo: str
        bar: int

    class SomeClassB(BaseModel):
        foo: str

    @app.request("subject_a", result=SomeClassA)
    def get_subject_a(app):
        return {"foo": "str", "bar": 2}

    @app.request("subject_b", result=SomeClassB)
    def get_subject_b(app):
        return {"foo": "str"}

    app.generate_asyncapi()
    schema = app.asyncapi_schema
    subject_a_reply_ref = schema["channels"]["natsapi.development.subject_a"]["request"]["replies"][0]["payload"][
        "$ref"
    ].split("/")[-1]
    subject_b_reply_ref = schema["channels"]["natsapi.development.subject_b"]["request"]["replies"][0]["payload"][
        "$ref"
    ].split("/")[-1]

    assert subject_a_reply_ref in schema["components"]["schemas"]
    assert subject_b_reply_ref in schema["components"]["schemas"]


async def test_generate_shema_w_docstring_should_generate_proper_description(app: NatsAPI):
    user_router = SubjectRouter(prefix="v1", tags=["users"])

    @user_router.request(
        "users.CREATE",
        result=CreateResult,
    )
    def create_base_user(app):
        """
        should be generated
        """
        return {}

    app.include_router(user_router)

    schema = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert (
        schema["channels"]["natsapi.development.v1.users.CREATE"]["request"].get("description") == "should be generated"
    )


async def test_generate_shema_w_description_in_route_should_overwrite_description(app: NatsAPI):
    user_router = SubjectRouter(prefix="v1", tags=["users"])

    @user_router.request(
        "users.CREATE",
        result=CreateResult,
        description="Creates user that can be used throughout the app",
    )
    def create_base_user(app):
        """
        should be generated
        """
        return {}

    app.include_router(user_router)

    schema = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert (
        schema["channels"]["natsapi.development.v1.users.CREATE"]["request"].get("description")
        == "Creates user that can be used throughout the app"
    )


async def test_generate_shema_w_routers_that_have_union_typing_should_generate(app: NatsAPI):
    class A(BaseModel):
        a: int

    class B(BaseModel):
        b: int

    r = SubjectRouter(prefix="v1")

    @r.request("union", result=Union[A, B])
    def union_result(app):
        return A(a=4)

    app.include_router(r)

    app.generate_asyncapi()
    schema = app.asyncapi_schema

    union_route = schema["channels"]["natsapi.development.v1.union"]
    union_route_replies = union_route["request"]["replies"]
    assert len(union_route_replies) == 2
    union_opts = union_route_replies[0]["payload"]["anyOf"]
    assert len(union_opts) == 2
    response_models = [m["$ref"].split("/")[-1] for m in union_opts]
    assert response_models == ["A", "B"]

    schema_from_request = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert schema_from_request == schema


async def test_given_no_func_name_should_use_subject_as_summary(app: NatsAPI):
    @app.request("foo", result=CreateResult)
    def _(app):
        return {}

    schema = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert schema["channels"]["natsapi.development.foo"]["request"]["summary"] == "Foo"


async def test_pub_and_req_should_render_properly(app: NatsAPI):
    @app.request("req", result=CreateResult)
    def _(app):
        return {}

    @app.publish("pub")
    def _(app):
        return {}

    schema = (await app.nc.request("natsapi.development.schema.RETRIEVE", {})).result
    assert schema["channels"]["natsapi.development.req"]["request"]["summary"] == "Req"
    assert schema["channels"]["natsapi.development.pub"]["publish"]["summary"] == "Pub"
