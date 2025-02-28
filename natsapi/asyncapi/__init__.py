from typing import Any

from pydantic import BaseModel, validator

from .models import ExternalDocumentation, Server


class Errors(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    upper_bound: int
    lower_bound: int
    errors: list[Any]

    @validator("lower_bound")
    def upper_bigger_than_lower(v, values):
        assert v < values["upper_bound"], "upper bound is smaller than lower bound"
        return v


__all__ = ["ExternalDocumentation", "Server", "Errors"]
