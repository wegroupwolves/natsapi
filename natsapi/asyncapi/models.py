from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

# TODO: Extend some classes with specifications object


class ExternalDocumentation(BaseModel):
    description: Optional[str]
    url: str


class Discriminator(BaseModel):
    propertyName: Dict[str, Any]
    mapping: Optional[Dict[str, str]] = None


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
    required: Optional[List[str]] = None
    enum: Optional[List[Any]] = None
    type: Optional[str] = None
    allOf: Optional[List[Any]] = None
    oneOf: Optional[List[Any]] = None
    anyOf: Optional[List[Any]] = None
    not_: Optional[Any] = Field(None, alias="not")
    items: Optional[Any] = None
    properties: Optional[Dict[str, Any]] = None
    additionalProperties: Optional[Union[Dict[str, Any], bool]] = None
    description: Optional[str] = None
    format: Optional[str] = None
    default: Optional[Any] = None
    nullable: Optional[bool] = None
    discriminator: Optional[Discriminator] = None
    readOnly: Optional[bool] = None
    writeOnly: Optional[bool] = None
    externalDocs: Optional[ExternalDocumentation] = None
    example: Optional[Any] = None
    deprecated: Optional[bool] = None


class Schema(SchemaBase):
    allOf: Optional[List[SchemaBase]] = None
    oneOf: Optional[List[SchemaBase]] = None
    anyOf: Optional[List[SchemaBase]] = None
    not_: Optional[SchemaBase] = Field(None, alias="not")
    items: Optional[SchemaBase] = None
    properties: Optional[Dict[str, SchemaBase]] = None
    additionalProperties: Optional[Union[Dict[str, Any], bool]] = None


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
    nats: Optional[Union[NatsBindings, Reference]]


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
    headers: Optional[Union[Schema, Reference]]
    correlationId: Optional[Union[CorrelationId, Reference]]
    schemaFormat: Optional[str]
    contentType: Optional[str]
    name: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    tags: Optional[List[Tag]]
    externalDocs: Optional[ExternalDocumentation]
    bindings: Optional[Union[MessageBindings, Reference]]
    examples: Optional[Dict[str, Any]]


class Message(BaseModel):
    headers: Optional[Union[Schema, Reference]] = None
    payload: Optional[Any] = None
    correlationId: Optional[Union[CorrelationId, Reference]] = None
    schemaFormat: Optional[str] = None
    contentType: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None
    bindings: Optional[Union[MessageBindings, Reference]] = None
    examples: Optional[Dict[str, Any]] = None
    traits: Optional[Union[MessageTrait, Reference]] = None


class OperationTrait(BaseModel):
    operationId: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None
    bindings: Optional[Union[OperationBindings, Reference]] = None


class Operation(BaseModel):
    operationId: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None
    bindings: Optional[Union[OperationBindings, Reference]] = None
    traits: Optional[List[Union[OperationTrait, Reference]]] = None
    message: Optional[Union[Message, Reference]] = None


class SubscribeOperation(Operation):
    queue: Optional[str] = Field(None, alias="x-queue")


class RequestOperation(Operation):
    replies: Optional[List[Union[Message, Reference]]] = None
    suggestedTimeout: Optional[float] = Field(None, alias="x-suggested-timeout")


class Parameter(BaseModel):
    description: Optional[str] = None
    schema_: Union[Dict[str, Any], Reference] = Field(..., alias="schema")
    location: Optional[str] = None


class ChannelItem(BaseModel):
    description: Optional[str] = None
    subscribe: Optional[SubscribeOperation] = None
    publish: Optional[Operation] = None
    request: Optional[RequestOperation] = None
    parameters: Optional[Dict[str, Union[Parameter, Reference]]] = None
    bindings: Optional[Union[ChannelBindings, Reference]] = None
    deprecated: bool | None = None


class ServerVariable(BaseModel):
    enum: Optional[List[str]] = None
    default: Optional[str] = None
    description: Optional[str] = None
    examples: Optional[List[str]] = None


class Server(BaseModel):
    url: str
    protocol: str
    protocolVersion: str | None
    description: Optional[str]
    variables: Optional[Dict[str, ServerVariable]]
    bindings: Optional[Union[ServerBindings, Reference]] = None


class Components(BaseModel):
    schemas: Optional[Dict[str, Union[Schema, Reference]]] = None
    messages: Optional[Dict[str, Union[Message, Reference]]] = None
    parameters: Optional[Dict[str, Union[Dict[str, Parameter], Reference]]] = None
    correlationIds: Optional[Dict[str, Union[CorrelationId, Reference]]] = None
    operationTraits: Optional[Dict[str, Union[OperationTrait, Reference]]] = None
    messageTraits: Optional[Dict[str, Union[MessageTrait, Reference]]] = None
    serverBindings: Optional[Dict[str, Union[ServerBindings, Reference]]] = None
    channelBindings: Optional[Dict[str, Union[ChannelBindings, Reference]]] = None
    operationBindings: Optional[Dict[str, Union[OperationBindings, Reference]]] = None
    messageBindings: Optional[Dict[str, Union[MessageBindings, Reference]]] = None


class Range(BaseModel):
    upper: int
    lower: int

    @validator("lower")
    def upper_bigger_than_lower(v, values):
        assert v < values["upper"], "upper bound is smaller than lower bound"
        return v


class Errors(BaseModel):
    range: Range = Field(..., alias="range")
    items: List[Any]


class AsyncAPI(BaseModel):
    asyncapi: str
    id: Optional[str] = None
    info: Info
    servers: Optional[Dict[str, Server]] = None
    defaultContentType: Optional[str] = "application/json"
    channels: Optional[Dict[str, Union[ChannelItem, Reference]]] = None
    components: Optional[Components] = None
    tags: Optional[List[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None
    errors: Optional[Errors] = None
