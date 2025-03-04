from typing import Any, Optional, Union

from pydantic import BaseModel, Field, validator

# TODO: Extend some classes with specifications object


class ExternalDocumentation(BaseModel):
    description: Optional[str]
    url: str


class Discriminator(BaseModel):
    propertyName: dict[str, Any]
    mapping: Optional[dict[str, str]] = None


class SchemaBase(BaseModel):
    ref: Optional[str] = Field(None, alias="$ref")
    title: Optional[str] = None
    multipleOf: Optional[float] = None
    maximum: Optional[float] = None
    exclusiveMaximum: Optional[float] = None
    minimum: Optional[float] = None
    exclusiveMinimum: Optional[float] = None
    maxLength: Optional[int] = Field(None, gte=0)
    minLength: Optional[int] = Field(None, gte=0)
    pattern: Optional[str] = None
    maxItems: Optional[int] = Field(None, gte=0)
    minItems: Optional[int] = Field(None, gte=0)
    uniqueItems: Optional[bool] = None
    maxProperties: Optional[int] = Field(None, gte=0)
    minProperties: Optional[int] = Field(None, gte=0)
    required: Optional[list[str]] = None
    enum: Optional[list[Any]] = None
    type: Optional[str] = None
    allOf: Optional[list[Any]] = None
    oneOf: Optional[list[Any]] = None
    anyOf: Optional[list[Any]] = None
    not_: Any = Field(None, alias="not")
    items: Any = None
    properties: Optional[dict[str, Any]] = None
    additionalProperties: Optional[Union[dict[str, Any], bool]] = None
    description: Optional[str] = None
    format: Optional[str] = None
    default: Any = None
    nullable: Optional[bool] = None
    discriminator: Optional[Discriminator] = None
    readOnly: Optional[bool] = None
    writeOnly: Optional[bool] = None
    externalDocs: Optional[ExternalDocumentation] = None
    example: Any = None
    deprecated: Optional[bool] = None


class Schema(SchemaBase):
    allOf: Optional[list[SchemaBase]] = None
    oneOf: Optional[list[SchemaBase]] = None
    anyOf: Optional[list[SchemaBase]] = None
    not_: Optional[SchemaBase] = Field(None, alias="not")
    items: Optional[SchemaBase] = None
    properties: Optional[dict[str, SchemaBase]] = None
    additionalProperties: Optional[Union[dict[str, Any], bool]] = None


class Contact(BaseModel):
    name: Optional[str]
    url: Optional[str]
    email: Optional[str]


class License(BaseModel):
    name: str
    url: Optional[str]


class Info(BaseModel):
    title: str
    version: str
    description: Optional[str] = None
    termsOfService: Optional[str] = None
    contact: Optional[Contact] = None
    licence: Optional[License] = None


class Reference(BaseModel):
    ref: str = Field(..., alias="$ref")


class Tag(BaseModel):
    name: str
    description: Optional[str] = None
    externalDocs: Optional[ExternalDocumentation] = None


# TODO: Add nats bindings
class NatsBindings(BaseModel):
    pass


class BindingsBase(BaseModel):
    nats: Union[NatsBindings, Reference, None]


class ServerBindings(BindingsBase):
    pass


class ChannelBindings(BindingsBase):
    pass


class OperationBindings(BindingsBase):
    pass


class MessageBindings(BindingsBase):
    pass


class CorrelationId(BaseModel):
    location: str
    description: Optional[str]


class MessageTrait(BaseModel):
    headers: Union[Schema, Reference, None]
    correlationId: Union[CorrelationId, Reference, None]
    schemaFormat: Optional[str]
    contentType: Optional[str]
    name: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    tags: Optional[list[Tag]]
    externalDocs: Optional[ExternalDocumentation]
    bindings: Union[MessageBindings, Reference, None]
    examples: Optional[dict[str, Any]]


class Message(BaseModel):
    headers: Union[Schema, Reference, None] = None
    payload: Any = None
    correlationId: Union[CorrelationId, Reference, None] = None
    schemaFormat: Optional[str] = None
    contentType: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None
    bindings: Union[MessageBindings, Reference, None] = None
    examples: Optional[dict[str, Any]] = None
    traits: Union[MessageTrait, Reference, None] = None


class OperationTrait(BaseModel):
    operationId: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None
    bindings: Union[OperationBindings, Reference, None] = None


class Operation(BaseModel):
    operationId: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None
    bindings: Union[OperationBindings, Reference, None] = None
    traits: Optional[list[Union[OperationTrait, Reference]]] = None
    message: Union[Message, Reference, None] = None


class SubscribeOperation(Operation):
    queue: Optional[str] = Field(None, alias="x-queue")


class RequestOperation(Operation):
    replies: Optional[list[Union[Message, Reference]]] = None
    suggestedTimeout: Optional[float] = Field(None, alias="x-suggested-timeout")


class Parameter(BaseModel):
    description: Optional[str] = None
    schema_: Union[dict[str, Any], Reference] = Field(..., alias="schema")
    location: Optional[str] = None


class ChannelItem(BaseModel):
    description: Optional[str] = None
    subscribe: Optional[SubscribeOperation] = None
    publish: Optional[Operation] = None
    request: Optional[RequestOperation] = None
    parameters: Optional[dict[str, Union[Parameter, Reference]]] = None
    bindings: Union[ChannelBindings, Reference, None] = None
    deprecated: Optional[bool] = None


class ServerVariable(BaseModel):
    enum: Optional[list[str]] = None
    default: Optional[str] = None
    description: Optional[str] = None
    examples: Optional[list[str]] = None


class Server(BaseModel):
    url: str
    protocol: str
    protocolVersion: Optional[str]
    description: Optional[str]
    variables: Optional[dict[str, ServerVariable]]
    bindings: Union[ServerBindings, Reference, None] = None


class Components(BaseModel):
    schemas: Optional[dict[str, Union[Schema, Reference]]] = None
    messages: Optional[dict[str, Union[Message, Reference]]] = None
    parameters: Optional[dict[str, Union[dict[str, Parameter], Reference]]] = None
    correlationIds: Optional[dict[str, Union[CorrelationId, Reference]]] = None
    operationTraits: Optional[dict[str, Union[OperationTrait, Reference]]] = None
    messageTraits: Optional[dict[str, Union[MessageTrait, Reference]]] = None
    serverBindings: Optional[dict[str, Union[ServerBindings, Reference]]] = None
    channelBindings: Optional[dict[str, Union[ChannelBindings, Reference]]] = None
    operationBindings: Optional[dict[str, Union[OperationBindings, Reference]]] = None
    messageBindings: Optional[dict[str, Union[MessageBindings, Reference]]] = None


class Range(BaseModel):
    upper: int
    lower: int

    @validator("lower")
    def upper_bigger_than_lower(v, values):
        assert v < values["upper"], "upper bound is smaller than lower bound"
        return v


class Errors(BaseModel):
    range: Range = Field(..., alias="range")
    items: list[Any]


class AsyncAPI(BaseModel):
    asyncapi: str
    id: Optional[str] = None
    info: Info
    servers: Optional[dict[str, Server]] = None
    defaultContentType: Optional[str] = "application/json"
    channels: Optional[dict[str, Union[ChannelItem, Reference]]] = None
    components: Optional[Components] = None
    tags: Optional[list[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None
    errors: Optional[Errors] = None
