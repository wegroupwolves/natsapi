from typing import Any, Optional, Union

from nats.aio.client import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_DRAIN_TIMEOUT,
    DEFAULT_MAX_FLUSHER_QUEUE_SIZE,
    DEFAULT_MAX_OUTSTANDING_PINGS,
    DEFAULT_MAX_RECONNECT_ATTEMPTS,
    DEFAULT_PENDING_SIZE,
    DEFAULT_PING_INTERVAL,
    DEFAULT_RECONNECT_TIME_WAIT,
    DEFAULT_SUB_PENDING_BYTES_LIMIT,
    DEFAULT_SUB_PENDING_MSGS_LIMIT,
)

from natsapi._compat import BaseSettings


class ConnectConfig(BaseSettings):
    servers: Union[str, list[str]] = ["nats://127.0.0.1:4222"]
    error_cb: Any = None
    closed_cb: Any = None
    reconnected_cb: Any = None
    disconnected_cb: Any = None
    discovered_server_cb: Any = None
    name: Any = None
    pedantic: Any = False
    verbose: Any = False
    allow_reconnect: Any = True
    connect_timeout: Any = DEFAULT_CONNECT_TIMEOUT
    reconnect_time_wait: Any = DEFAULT_RECONNECT_TIME_WAIT
    max_reconnect_attempts: Any = DEFAULT_MAX_RECONNECT_ATTEMPTS
    ping_interval: Any = DEFAULT_PING_INTERVAL
    max_outstanding_pings: Any = DEFAULT_MAX_OUTSTANDING_PINGS
    dont_randomize: Any = False
    flusher_queue_size: Any = DEFAULT_MAX_FLUSHER_QUEUE_SIZE
    no_echo: Any = False
    tls: Any = None
    tls_hostname: Any = None
    user: Any = None
    password: Any = None
    token: Any = None
    drain_timeout: Any = DEFAULT_DRAIN_TIMEOUT
    signature_cb: Any = None
    user_jwt_cb: Any = None
    user_credentials: Any = None
    nkeys_seed: Optional[str] = None
    flush_timeout: Optional[float] = None
    pending_size: int = DEFAULT_PENDING_SIZE


class SubscribeConfig(BaseSettings):
    queue: Any = ""
    future: Any = None
    max_msgs: Any = 0
    pending_msgs_limit: Any = DEFAULT_SUB_PENDING_MSGS_LIMIT
    pending_bytes_limit: Any = DEFAULT_SUB_PENDING_BYTES_LIMIT


class Config(BaseSettings):
    connect: ConnectConfig = ConnectConfig()
    subscribe: SubscribeConfig = SubscribeConfig()


default_config = Config()
