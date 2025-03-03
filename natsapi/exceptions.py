from typing import Any


class NatsAPIError(RuntimeError): ...


class DuplicateRouteException(NatsAPIError):
    """
    Raised when a route with the same nats subject is added to app.
    """

    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return f"{self.__class__.__name__} {self.msg}"


class JsonRPCException(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data


class JsonRPCRequestException(JsonRPCException):
    def __init__(self, data: Any = None):
        self.code = -32600
        self.message = "INVALID_REQUEST_FORMAT"
        self.data = data


class JsonRPCUnknownMethodException(JsonRPCException):
    def __init__(self, data: Any = None):
        self.code = -32601
        self.message = "NO_SUCH_ENDPOINT"
        self.data = data


class JsonRPCInvalidMethodParamsException(JsonRPCException):
    def __init__(self, message, data: Any = None):
        self.code = -32602
        self.message = message
        self.data = data


class JsonRPCInternalErrorException(JsonRPCException):
    def __init__(self, data: Any = None):
        self.code = -32603
        self.message = "INTERNAL_ERROR"
        self.data = data


class JsonRPCInvalidParamsException(JsonRPCException):
    def __init__(self, data: Any = None):
        self.code = -32602
        self.message = "INVALID_PARAMETERS_RECEIVED"
        self.data = data
