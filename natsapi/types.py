"""Yanked from FastApi.typing"""
from typing import Any, Callable, TypeVar

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])
