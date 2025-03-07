from typing import Optional
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError
from pydantic.fields import Field

from natsapi.models import JsonRPCError, JsonRPCReply, JsonRPCRequest


def test_change_param_type_of_model_should_change():
    class Params(BaseModel):
        foo: int = Field(...)
        bar: Optional[str] = Field(None)

    new_model = JsonRPCRequest.with_params(Params)

    payload = {"params": {"foo": 22}, "timeout": 60}
    created_request = JsonRPCRequest.parse_obj(payload)
    d = new_model.parse_raw(created_request.json())
    actual = new_model.parse_obj(d).params
    expected = Params

    assert type(actual) is expected


def test_result_or_error_should_be_provided_in_jsonrpcreply():
    with pytest.raises(ValidationError) as e:
        JsonRPCReply(id=uuid4())
    assert "A result or error should be required" in str(e.value), e.value


def test_result_and_error_should_not_be_provided_at_same_time_in_jsonrpcreply():
    with pytest.raises(AttributeError) as e:
        JsonRPCReply(error={"code": 1, "message": "foobar"}, result={"status": "OK"})
    assert "An RPC reply MUST NOT have an error and a result" in str(e)


def test_jsponrpcerror_timestamp_is_generated_on_creation():
    error_1 = JsonRPCError(code=1, message="", data=None)
    error_2 = JsonRPCError(code=1, message="", data=None)
    assert error_1.timestamp != error_2.timestamp
