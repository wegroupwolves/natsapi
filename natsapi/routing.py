import inspect
from collections.abc import Callable
from typing import Any, Optional

from pydantic import BaseModel

from natsapi.asyncapi import ExternalDocumentation
from natsapi.types import DecoratedCallable
from natsapi.utils import create_field, generate_operation_id_for_subject, get_request_model, get_summary


class Request:
    def __init__(
        self,
        subject: str,
        endpoint: Callable[..., Any],
        *,
        result=type[Any],
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        include_schema: Optional[bool] = True,
        suggested_timeout: Optional[float] = None,
    ):
        self.subject = subject
        self.endpoint = endpoint
        self.skip_validation = skip_validation
        self.summary = summary or get_summary(endpoint) or subject
        self.operation_id = generate_operation_id_for_subject(summary=self.summary, subject=self.subject)
        self.result = result
        self.params = get_request_model(self.endpoint, subject, self.skip_validation)
        reply_name = "Reply_" + self.operation_id
        request_name = "Request_" + self.operation_id
        self.reply_field = create_field(name=reply_name, type_=self.params)
        self.request_field = create_field(name=request_name, type_=self.result)

        self.tags = tags or []
        self.description = description or ""
        self.description = description or inspect.cleandoc(self.endpoint.__doc__ or "")
        self.deprecated = deprecated
        self.include_schema = include_schema
        self.suggested_timeout = suggested_timeout

        assert callable(endpoint), "An endpoint must be callable"


class Publish:
    def __init__(
        self,
        subject: str,
        endpoint: Callable[..., Any],
        *,
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        include_schema: Optional[bool] = True,
    ):
        self.subject = subject
        self.endpoint = endpoint
        self.skip_validation = skip_validation
        self.summary = summary or get_summary(endpoint) or subject
        self.operation_id = generate_operation_id_for_subject(summary=self.summary, subject=self.subject)
        self.params = get_request_model(self.endpoint, subject, self.skip_validation)
        reply_name = "Reply_" + self.operation_id
        self.reply_field = create_field(name=reply_name, type_=self.params)

        self.tags = tags or []
        self.description = description or ""
        self.description = description or inspect.cleandoc(self.endpoint.__doc__ or "")
        self.deprecated = deprecated
        self.include_schema = include_schema

        assert callable(endpoint), "An endpoint must be callable"


class Sub:
    def __init__(
        self,
        subject: str,
        *,
        queue: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ):

        self.subject = subject
        self.queue = queue
        self.summary = summary
        self.description = description
        self.tags = tags or []
        self.externalDocs = externalDocs


class Pub:
    def __init__(
        self,
        subject: str,
        params: BaseModel,
        *,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ):
        self.subject = subject
        self.summary = summary
        self.description = description
        self.tags = tags or []
        self.externalDocs = externalDocs
        self.params = params
        self.params_field = create_field(name="Publish_" + subject, type_=self.params)


class SubjectRouter:
    def __init__(
        self,
        *,
        prefix: str = None,
        tags: Optional[list[str]] = None,
        routes: Optional[list[Request]] = None,
        subs: Optional[set[Sub]] = None,
        pubs: Optional[set[Pub]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
    ) -> None:
        self.prefix = prefix
        self.routes = routes or []
        self.pubs = pubs or set()
        self.subs = subs or set()
        self.tags: list[str] = tags or []
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema

    def add_request(
        self,
        subject: str,
        endpoint: Callable[..., Any],
        *,
        result=type[Any],
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        suggested_timeout: Optional[float] = None,
        include_schema: Optional[bool] = True,
    ) -> None:
        current_tags = self.tags.copy()
        if tags:
            current_tags.extend(tags)
        current_subject = ".".join([self.prefix, subject]) if self.prefix is not None else subject
        subject = Request(
            subject=current_subject,
            endpoint=endpoint,
            result=result,
            skip_validation=skip_validation,
            description=description,
            deprecated=deprecated if deprecated is not None else self.deprecated,
            tags=current_tags,
            summary=summary,
            suggested_timeout=suggested_timeout,
            include_schema=include_schema,
        )
        self.routes.append(subject)

    def add_publish(
        self,
        subject: str,
        endpoint: Callable[..., Any],
        *,
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        include_schema: Optional[bool] = True,
    ) -> None:
        current_tags = self.tags.copy()
        if tags:
            current_tags.extend(tags)
        current_subject = ".".join([self.prefix, subject]) if self.prefix is not None else subject
        subject = Publish(
            subject=current_subject,
            endpoint=endpoint,
            skip_validation=skip_validation,
            description=description,
            deprecated=deprecated if deprecated is not None else self.deprecated,
            tags=current_tags,
            summary=summary,
            include_schema=include_schema,
        )
        self.routes.append(subject)

    def request(
        self,
        subject: str,
        *,
        result=type[Any],
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        suggested_timeout: Optional[float] = None,
        include_schema: Optional[bool] = True,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_request(
                subject=subject,
                endpoint=func,
                result=result,
                skip_validation=skip_validation,
                description=description,
                deprecated=deprecated,
                tags=tags,
                summary=summary,
                suggested_timeout=suggested_timeout,
                include_schema=include_schema,
            )
            return func

        return decorator

    def publish(
        self,
        subject: str,
        *,
        result=type[Any],
        skip_validation: Optional[bool] = False,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        include_schema: Optional[bool] = True,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_publish(
                subject=subject,
                endpoint=func,
                skip_validation=skip_validation,
                description=description,
                deprecated=deprecated,
                tags=tags,
                summary=summary,
                include_schema=include_schema,
            )
            return func

        return decorator

    def add_pub(
        self,
        subject: str,
        params: BaseModel,
        *,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ) -> None:
        """
        Include pub in asyncapi schema
        """
        pub = Pub(
            subject,
            params,
            summary=summary,
            description=description,
            tags=tags or None,
            externalDocs=externalDocs,
        )
        self.pubs.add(pub)

    def pub(
        self,
        subject: str,
        *,
        params=type[Any],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_pub(
                subject=subject,
                params=params,
                summary=summary,
                description=description,
                tags=tags,
                externalDocs=externalDocs,
            )
            return func

        return decorator

    def add_sub(
        self,
        subject: str,
        *,
        queue: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ) -> None:
        """
        Include sub in asyncapi schema
        """
        sub = Sub(
            subject,
            queue=queue,
            summary=summary,
            description=description,
            tags=tags or None,
            externalDocs=externalDocs,
        )
        self.subs.add(sub)

    def sub(
        self,
        subject: str,
        *,
        queue: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        summary: Optional[str] = None,
        externalDocs: Optional[ExternalDocumentation] = None,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_sub(
                subject=subject,
                queue=queue,
                summary=summary,
                description=description,
                tags=tags,
                externalDocs=externalDocs,
            )
            return func

        return decorator
