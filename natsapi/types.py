"""Yanked from FastApi.typing"""

from collections.abc import Callable
from typing import Any, TypeVar

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])
