import logging

from pydantic import ValidationError

from natsapi.exceptions import JsonRPCException
from natsapi.models import ErrorData, JsonRPCError, JsonRPCRequest


def get_validation_target(e):
    err_loc_tree = [str(loc_part) for loc_part in e["loc"]]
    target = ".".join(err_loc_tree)
    return target


def handle_jsonrpc_exception(exc: JsonRPCException, request: JsonRPCRequest, subject: str) -> JsonRPCError:
    try:
        data = ErrorData.parse_obj(exc.data)
    except Exception:
        data = ErrorData(type=type(exc).__name__, errors=[])
    logging.error(
        exc,
        exc_info=True,
        stack_info=True,
        extra={
            "json_rpc_id": request.id,
            "auth": request.params.get("auth"),
            "json": request.dict(),
            "subject": subject,
            "NATS": True,
            "code": exc.code,
        },
    )
    return JsonRPCError(code=exc.code, message=exc.message, data=data)


def handle_validation_error(exc: ValidationError, request: JsonRPCRequest, subject: str) -> JsonRPCError:
    errors = []
    for ve in exc.errors():
        detail_target = get_validation_target(ve)
        detail_msg = ve["msg"]
        errors.append({"type": type(exc).__name__, "target": detail_target, "message": detail_msg})

    logging.error(
        exc,
        exc_info=True,
        stack_info=True,
        extra={
            "json_rpc_id": request.id,
            "auth": request.params.get("auth"),
            "json": request.dict(),
            "subject": subject,
            "NATS": True,
            "code": -40001,
        },
    )
    data = ErrorData(type=type(exc).__name__, errors=errors)
    msg = "Invalid data was provided or some data is missing."
    return JsonRPCError(code=-40001, message=msg, data=data)


def handle_internal_error(exc: Exception, request: JsonRPCRequest, subject: str) -> JsonRPCError:
    code = -40000
    try:
        # Try parsing FormattedException variants
        code = exc.rpc_code
        message = f"{exc.msg}: {exc.detail}"
    except Exception:
        message = str(exc)
        code = -40000
    logging.error(
        exc,
        exc_info=True,
        stack_info=True,
        extra={
            "json_rpc_id": request.id,
            "auth": request.params.get("auth"),
            "json": request.dict(),
            "subject": subject,
            "NATS": True,
            "code": code,
        },
    )
    data = ErrorData(type=type(exc).__name__, errors=[])
    return JsonRPCError(code=code, message=message, data=data)
