import collections
import inspect
import re
from collections.abc import Callable
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import FieldInfo
from pydantic.v1.schema import model_process_schema

from natsapi._compat import PYDANTIC_V2, ModelField
from natsapi.asyncapi.constants import REF_PREFIX
from natsapi.exceptions import NatsAPIError


def get_summary(endpoint: Callable) -> str:
    """Yanked from `Starlette.routing`"""
    if inspect.isfunction(endpoint) or inspect.isclass(endpoint):
        return endpoint.__name__ if endpoint.__name__ != "_" else None
    return endpoint.__class__.__name__


def generate_operation_id_for_subject(*, summary: str, subject: str) -> str:
    operation_id = summary + "_" + subject
    operation_id = re.sub("[^0-9a-zA-Z_]", "_", operation_id)
    return operation_id


def create_field(
    name: str,
    type_: type[Any],
    class_validators: Optional[dict[str, Any]] = None,
    model_config: type[BaseConfig] = BaseConfig,
    field_info: Optional[FieldInfo] = None,
) -> ModelField:
    """
    Yanked from fastapi.utils
    Create a new reply field. Raises if type_ is invalid.
    """
    class_validators = class_validators or {}

    field_info = (field_info or FieldInfo(annotation=type_)) if PYDANTIC_V2 else (field_info or FieldInfo())

    kwargs = {"name": name, "field_info": field_info}

    if not PYDANTIC_V2:
        kwargs.update(
            {
                "type_": type_,
                "class_validators": class_validators,
                "model_config": model_config,
                "required": True,
            },
        )

    try:
        return ModelField(**kwargs)
    except RuntimeError as e:
        raise NatsAPIError(
            f"Invalid args for reply field! Hint: check that {type_} is a valid pydantic field type",
        ) from e


def get_model_definitions(
    *,
    flat_models: Union[set[type[BaseModel], type[Enum]]],
    model_name_map: Union[dict[type[BaseModel], type[Enum], str]],
) -> dict[str, Any]:
    definitions: dict[str, dict[str, Any]] = {}
    for model in flat_models:
        m_schema, m_definitions, m_nested_models = model_process_schema(
            model,
            model_name_map=model_name_map,
            ref_prefix=REF_PREFIX,
        )
        definitions.update(m_definitions)
        try:
            model_name = model_name_map[model]
        except KeyError as exc:
            method_name = str(exc.args[0]).replace("<class 'pydantic.main.", "").replace("_params'>", "")
            raise NatsAPIError(
                f"Could not generate schema. Two or more functions share the name '{method_name}'. Make sure methods don't share the same name",
            ) from exc
        definitions[model_name] = m_schema
    return definitions


def get_request_model(func: Callable, subject: str, skip_validation: bool):
    parameters = collections.OrderedDict(inspect.signature(func).parameters)
    name_prefix = func.__name__ if func.__name__ != "_" else subject

    if skip_validation:
        assert (
            "kwargs" in parameters
        ), f"Add '**kwargs' to the '{name_prefix}' method as extra arguments can be passed in payload and won't be filtered out."

    param_fields = {}
    valid_app_types = ("FastAPI", "NatsAPI", "_empty")
    for i, parameter in enumerate(parameters.values()):
        if i == 0:
            assert parameter.name == "app", "First parameter should be named 'app'"
            if parameter.annotation == Any:
                continue
            else:
                assert (
                    parameter.annotation.__name__ in valid_app_types
                ), f"Valid types for app are: NatsAPI, FastAPI, or Any. Got {parameter.annotation.__name__}"
                continue

        if parameter.name in ["args", "kwargs"] and skip_validation:
            continue
        else:
            assert parameter.annotation is not inspect._empty, f"{parameter.name} has no type"
            default = ... if parameter.default is inspect._empty else parameter.default
            param_fields[parameter.name] = (parameter.annotation, default)

    model = create_model(f"{name_prefix}_params", **param_fields)
    return model
