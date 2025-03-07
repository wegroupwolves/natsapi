from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, create_model, root_validator, validator

from natsapi.enums import JSON_RPC_VERSION


class ErrorDetail(BaseModel):
    type: str
    target: Optional[str] = None
    message: str


class ErrorData(BaseModel):
    type: Optional[str] = None
    errors: list[ErrorDetail] = []


class JsonRPCError(BaseModel):
    code: int = Field(..., description="Error code that falls in the predefined error range for this type of exception")
    message: str = Field(
        ...,
        description="A message providing a short description of the error.  SHOULD be limited to a concise single sentence",
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of when the error occured")
    data: Any = Field(None, description="Additional information about the error")


class JsonRPCReply(BaseModel):
    jsonrpc: JSON_RPC_VERSION = Field("2.0")
    id: UUID = Field(...)
    result: Optional[dict[str, Any]] = Field(None)
    error: Optional[JsonRPCError] = Field(None)

    @root_validator(pre=True)
    def check_result_and_error(cls, values):
        result, error = values.get("result"), values.get("error")
        assert result or error, "A result or error should be required"
        if result and error:
            raise AttributeError(
                "An RPC reply MUST NOT have an error and a result. Based on the result, you should provide only one.",
            )
        return values


class JsonRPCRequest(BaseModel):
    jsonrpc: Optional[JSON_RPC_VERSION] = Field("2.0")
    timeout: Optional[float] = Field(
        None,
        description="Timeout set by client, should be equal to the timeout set when doing nc.request, if publish use '-1'",
    )
    method: Optional[str] = Field(None, description="Request method used")
    params: dict[str, Any] = Field(...)
    id: Optional[UUID] = Field(None, alias="id", description="UUID created at the creation of the request")

    @validator("id", pre=True, always=True)
    def set_id(cls, id):
        return id or uuid4()

    @classmethod
    def with_params(self, params: BaseModel):
        return create_model("JsonRPC" + params.__name__, __base__=self, params=(params, ...))
