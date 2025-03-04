import typing

import pytest
from pydantic import BaseModel

from natsapi import NatsAPI, SubjectRouter


class StatusResult(BaseModel):
    status: typing.Any


class FastAPI(BaseModel):
    pass


async def test_method_parameters_should_get_parsed_to_correct_typing(app):
    class ThemesCreateCmd(BaseModel):
        primary: str
        color: typing.Union[str, None] = None

    @app.request("themes.CREATE", result=StatusResult)
    async def create_theme(app, data: ThemesCreateCmd):
        return {"status": data.primary}

    reply = await app.nc.request("natsapi.development.themes.CREATE", {"data": {"primary": "blue"}})

    assert reply.result["status"] == "blue"


def test_app_parameter_typing_should_validate_type():
    router = SubjectRouter()

    @router.request("themes.CONVERT", result=StatusResult)
    async def convert_theme(app):
        return {"status": "OK"}

    @router.request("themes.CREATE", result=StatusResult)
    async def create_theme(app: NatsAPI):
        return {"status": "OK"}

    @router.request("themes.DELETE", result=StatusResult)
    async def delete_theme(app: FastAPI):
        return {"status": "OK"}

    @router.request("themes.UPDATE", result=StatusResult)
    async def update_theme(app: typing.Any):
        return {"status": "OK"}

    with pytest.raises(AssertionError) as exc:

        @router.request("themes.CALCULATE", result=StatusResult)
        async def calculate_theme(app: int):
            return {"status": "OK"}

    assert "Got int" in str(exc)


class TypeResult(BaseModel):
    typing: str


async def test_exotic_typing_should_convert_to_correct_type(app):
    @app.request("themes.CONVERT", result=TypeResult)
    async def convert_theme(app, param: typing.Union[list[str], int]):
        return {"typing": type(param).__name__}

    reply = await app.nc.request("natsapi.development.themes.CONVERT", {"param": ["foo", "bar", "baz"]})
    assert reply.result["typing"] == "list"

    reply = await app.nc.request("natsapi.development.themes.CONVERT", {"param": 42})
    assert reply.result["typing"] == "int"

    reply = await app.nc.request("natsapi.development.themes.CONVERT", {"param": "NOT A LIST OR INT"})
    assert reply.error.code == -40001  # Validation Error
