import typing


from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Type, Union

from pydantic import BaseModel
from natsapi._compat import (
    ModelField,
    lenient_issubclass,
    get_cached_model_fields,
    get_compat_model_name_map,
    get_definitions,
    GenerateJsonSchema,
)

# from pydantic.schema import get_flat_models_from_fields, get_model_name_map
from pydantic.v1.schema import (
    get_flat_models_from_fields,
    get_model_name_map,
    get_flat_models_from_field,
    get_flat_models_from_model,
)

from natsapi.asyncapi.constants import REF_PREFIX, REF_TEMPLATE
from natsapi.encoders import jsonable_encoder
from natsapi.models import JsonRPCError
from natsapi.routing import Pub, Publish, Request, Sub
from natsapi.utils import get_model_definitions

from . import Errors, ExternalDocumentation, Server
from .models import AsyncAPI


def _get_flat_fields_from_params(fields: List[ModelField]) -> List[ModelField]:
    if not fields:
        return fields
    first_field = fields[0]
    if len(fields) == 1 and lenient_issubclass(first_field.type_, BaseModel):
        fields_to_extract = get_cached_model_fields(first_field.type_)
        return fields_to_extract
    return fields


def get_flat_models_from_routes(
    routes: Sequence[Request], pubs: Sequence[Pub]
) -> Set[Union[Type[BaseModel], Type[Enum]]]:
    replies_from_routes: Set[ModelField] = set()
    requests_from_routes: Set[ModelField] = set()
    messages_from_pubs: Set[ModelField] = set()
    for route in routes:
        if getattr(route, "include_schema", True) and isinstance(route, Request):
            if route.result:
                replies_from_routes.add(route.request_field)
            if route.params:
                replies_from_routes.add(route.reply_field)
        elif getattr(route, "include_schema", True) and isinstance(route, Publish):
            if route.params:
                replies_from_routes.add(route.reply_field)
    for pub in pubs:
        messages_from_pubs.add(pub.params_field)

    inputs = replies_from_routes | requests_from_routes | messages_from_pubs

    flat_models = _get_flat_fields_from_params([x for x in inputs])
    return flat_models


def get_flat_response_models(r) -> List[Type[BaseModel]]:
    """
    Returns flattened collection of response models of a route.
    If the response models are of typing.Union, a list of possible response models is returned.

    :r Single or multiple response models
    """
    if type(r) is typing._UnionGenericAlias:
        return list(r.__args__)
    else:
        return [r]


def get_asyncapi_request_operation_metadata(operation: Request) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    metadata["summary"] = operation.summary.replace("_", " ").title()
    metadata["description"] = operation.description

    if operation.tags:
        metadata["tags"] = operation.tags
    metadata["operationId"] = operation.operation_id
    if operation.deprecated:
        metadata["deprecated"] = operation.deprecated
    if timeout := getattr(operation, "suggested_timeout", None):
        metadata["x-suggested-timeout"] = timeout
    return metadata


def generate_asyncapi_request_channel(operation: Request, model_name_map: Dict[str, Any]) -> Any:

    operation_results = get_flat_response_models(operation.result)

    request_field_ref: str = REF_PREFIX + operation.params.__name__
    reply_field_refs: str = [REF_PREFIX + o.__name__ for o in operation_results]
    failed_reply_ref: str = REF_PREFIX + JsonRPCError.__name__

    operation_schema = get_asyncapi_request_operation_metadata(operation)
    payload = {"payload": {"$ref": request_field_ref}}
    operation_schema["message"] = payload
    replies = []
    if len(reply_field_refs) > 1:
        anyofs = [{"$ref": r} for r in reply_field_refs]
        replies.append({"payload": {"anyOf": anyofs}})
    else:
        replies.append({"payload": {"$ref": reply_field_refs[0]}})
    replies.append({"payload": {"$ref": failed_reply_ref}})
    operation_schema["tags"] = [{"name": tag} for tag in operation.tags]

    operation_schema["replies"] = replies
    return {"request": operation_schema, "deprecated": operation.deprecated}


def generate_asyncapi_publish_channel(operation: Publish, model_name_map: Dict[str, Any]) -> Any:
    request_field_ref: str = REF_PREFIX + operation.params.__name__

    operation_schema = get_asyncapi_request_operation_metadata(operation)
    payload = {"payload": {"$ref": request_field_ref}}
    operation_schema["message"] = payload
    operation_schema["tags"] = [{"name": tag} for tag in operation.tags]
    return {"publish": operation_schema, "deprecated": operation.deprecated}


def domain_errors_schema(lower_bound: int, upper_bound: int, exceptions: List[Exception]):
    schema = {}
    schema["range"] = {"upper": upper_bound, "lower": lower_bound}
    errors = []
    for exc in exceptions:
        try:
            error = exc(data="")
        except Exception:
            # Quick fix for FormattedException
            error = exc(detail="")

        if hasattr(error, "rpc_code"):
            code = error.rpc_code
        elif hasattr(error, "code"):
            code = error.code
        else:
            raise AttributeError(f"'{exc}' has no 'code' or 'rpc_code' attribute")

        if hasattr(error, "msg"):
            message = error.msg
        elif hasattr(error, "message"):
            message = error.message
        else:
            raise AttributeError(f"'{exc}' has no 'message' or 'msg' attribute")

        errors.append({"code": code, "message": message})
    schema["items"] = errors
    return schema


def get_sub_operation_schema(sub: Sub) -> Tuple[str, Dict[str, Any]]:
    _sub = {
        "summary": sub.summary,
        "description": sub.description,
        "tags": [{"name": tag} for tag in sub.tags] if len(sub.tags) > 0 else None,
        "externalDocs": sub.externalDocs,
        "message": {"summary": sub.summary},
    }
    op = {"subscribe": _sub}
    return sub.subject, op


def get_pub_operation_schema(pub: Pub, model_name_map: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    # pub_payload: str = REF_PREFIX + model_name_map[pub.params]
    pub_payload: str = REF_PREFIX + pub.params.__name__

    _pub = {
        "summary": pub.summary,
        "description": pub.description,
        "externalDocs": pub.externalDocs,
        "message": {"payload": {"$ref": pub_payload}, "pub": pub.summary},
        "tags": [{"name": tag} for tag in pub.tags] if len(pub.tags) > 0 else None,
    }
    op = {"publish": _pub}
    return pub.subject, op


def get_asyncapi(
    title: str,
    version: str,
    asyncapi_version: str,
    external_docs: ExternalDocumentation,
    errors: Errors,
    routes: Dict[str, Request],
    subs: List[Sub],
    pubs: List[Pub],
    description: Optional[str] = None,
    servers: Optional[Dict[str, Server]] = None,
) -> Dict[str, Any]:
    subjects: Dict[str, Dict[str, Any]] = {}
    info = {"title": title, "version": version}
    info["description"] = description if description else None
    components: Dict[str, Dict[str, Any]] = {}

    output: Dict[str, Any] = {"asyncapi": asyncapi_version, "info": info}

    flat_models = get_flat_models_from_routes(routes.values(), pubs)
    model_name_map = get_compat_model_name_map(flat_models)
    schema_generator = GenerateJsonSchema(ref_template=REF_TEMPLATE)

    # TODO:  <26-02-25, Sebastiaan Van Hoecke> # Where to use the first paramter (see https://github.com/fastapi/fastapi/blob/master/fastapi/openapi/utils.py#L493)
    _, definitions = get_definitions(
        fields=flat_models, schema_generator=schema_generator, model_name_map=model_name_map
    )
    definitions[JsonRPCError.__name__] = JsonRPCError.schema()
    components["schemas"] = definitions

    # if bool(flat_models):
    if 1:
        subjects: Dict[str, Dict[str, Any]] = {}
        for subject, endpoint in routes.items():
            if getattr(endpoint, "include_schema", None) and isinstance(endpoint, Request):
                result = generate_asyncapi_request_channel(endpoint, model_name_map)
                subjects[subject] = result
            elif getattr(endpoint, "include_schema", None) and isinstance(endpoint, Publish):
                result = generate_asyncapi_publish_channel(endpoint, model_name_map)
                subjects[subject] = result

    for sub in subs:
        channel, operation = get_sub_operation_schema(sub)

        subjects[channel] = operation

    for pub in pubs:
        channel, operation = get_pub_operation_schema(pub, model_name_map)
        subjects[channel] = operation

    info["description"] = description if description else None
    output: Dict[str, Any] = {"asyncapi": asyncapi_version, "info": info}
    output["servers"] = servers if {n: s.dict() for n, s in servers.items()} else None

    output["externalDocs"] = external_docs.dict() if external_docs else None
    output["errors"] = domain_errors_schema(errors.lower_bound, errors.upper_bound, errors.errors) if errors else None

    output["channels"] = subjects if len(subjects) > 0 else None
    output["components"] = components

    return jsonable_encoder(AsyncAPI(**output), by_alias=True, exclude_none=True)
