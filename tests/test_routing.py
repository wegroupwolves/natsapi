import pytest
from pydantic import BaseModel

from natsapi import NatsAPI, SubjectRouter


class NotificationParams(BaseModel):
    notification: str
    service: str


class StatusResult(BaseModel):
    status: str


def test_use_request_method_decorated_should_add_subject_to_router():
    app = NatsAPI("natsapi.development")

    router = SubjectRouter(prefix="v1")

    @router.request("test.CREATE", result=StatusResult)
    def _(app) -> StatusResult:
        return {"status": "OK"}

    app.include_router(router)

    assert len(app.routes) == len(router.routes)


def test_add_pub_should_add_pub_to_router(app: NatsAPI):
    router = SubjectRouter()

    @router.pub("*.subject.>", params=NotificationParams)
    @router.request("subject.RETRIEVE", result=StatusResult)
    async def _(app: NatsAPI):
        await app.nc.publish("notifications.CREATE", {"notification": "Hi", "service": "SMT"})
        return {"status": "OK"}

    app.include_router(router)
    assert len(app.pubs) == 1


def test_add_sub_should_add_sub_to_router(app: NatsAPI):
    router = SubjectRouter()

    @router.sub("*.subject.>", queue="natsapi")
    @router.request("subject.RETRIEVE", result=StatusResult)
    async def _(app: NatsAPI):
        await app.nc.subscribe("*.subject.>", queue="natsapi", cb=lambda _: print("some callback"))
        return {"status": "OK"}

    app.include_router(router)
    assert len(app.subs) == 2


def test_add_route_w_skip_validation_but_no_args_kwargs_should_throw_error(app):
    with pytest.raises(AssertionError):

        @app.request("skip_validation.CREATE", result=StatusResult, skip_validation=True)
        def skip_validation(app):
            return {"status": "OK"}


def test_two_routes_with_same_subject_should_throw_clear_exception_w_subject_router(app: NatsAPI):
    router = SubjectRouter()

    @router.request("foo", result=StatusResult)
    async def _(app: NatsAPI):  # noqa: F811
        return {"status": "OK"}

    @router.request("foo", result=StatusResult)
    async def _(app: NatsAPI):  # noqa: F811
        return {"status": "OK"}

    with pytest.raises(Exception) as e:
        app.include_router(router, root_path="foo")
    assert "defined twice" in str(e.value)


def test_pub_and_sub_with_same_subject_should_throw_clear_exception(app: NatsAPI):
    @app.publish("foo")
    async def _(app: NatsAPI):  # noqa: F811
        return {"status": "OK"}

    with pytest.raises(Exception) as e:

        @app.request("foo", result=StatusResult)
        async def _(app: NatsAPI):  # noqa: F811
            return {"status": "OK"}

    assert "defined twice" in str(e.value)


def test_two_pubs_with_same_subject_should_throw_clear_exception(app: NatsAPI):
    @app.publish("foo")
    async def _(app: NatsAPI):  # noqa: F811
        return {"status": "OK"}

    with pytest.raises(Exception) as e:

        @app.publish("foo")
        async def _(app: NatsAPI):  # noqa: F811
            return {"status": "OK"}

    assert "defined twice" in str(e.value)


def test_two_reqs_with_same_subject_should_throw_clear_exception(app: NatsAPI):
    @app.request("foo")
    async def _(app: NatsAPI):  # noqa: F811
        return {"status": "OK"}

    with pytest.raises(Exception) as e:

        @app.request("foo")
        async def _(app: NatsAPI):  # noqa: F811
            return {"status": "OK"}

    assert "defined twice" in str(e.value)
