import contextvars

CTX_JSONRPC_ID = contextvars.ContextVar("jsonrpc_id")

__all__ = ["CTX_JSONRPC_ID"]
