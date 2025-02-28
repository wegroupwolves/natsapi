from typing import Any

from pydantic import BaseModel, Field, validator

# TODO: Extend some classes with specifications object


class ExternalDocumentation(BaseModel):
    description: str | None
    url: str


class Discriminator(BaseModel):
    propertyName: dict[str, Any]
    mapping: dict[str, str] | None = None


class SchemaBase(BaseModel):
    ref: str | None = Field(None, alias="$ref")
    title: str | None = None
    multipleOf: float | None = None
    maximum: float | None = None
    exclusiveMaximum: float | None = None
    minimum: float | None = None
    exclusiveMinimum: float | None = None
    maxLength: int | None = Field(None, gte=0)
    minLength: int | None = Field(None, gte=0)
    pattern: str | None = None
    maxItems: int | None = Field(None, gte=0)
    minItems: int | None = Field(None, gte=0)
    uniqueItems: bool | None = None
    maxProperties: int | None = Field(None, gte=0)
    minProperties: int | None = Field(None, gte=0)
    required: list[str] | None = None
    enum: list[Any] | None = None
    type: str | None = None
    allOf: list[Any] | None = None
    oneOf: list[Any] | None = None
    anyOf: list[Any] | None = None
    not_: Any | None = Field(None, alias="not")
    items: Any | None = None
    properties: dict[str, Any] | None = None
    additionalProperties: dict[str, Any] | bool | None = None
    description: str | None = None
    format: str | None = None
    default: Any | None = None
    nullable: bool | None = None
    discriminator: Discriminator | None = None
    readOnly: bool | None = None
    writeOnly: bool | None = None
    externalDocs: ExternalDocumentation | None = None
    example: Any | None = None
    deprecated: bool | None = None


class Schema(SchemaBase):
    allOf: list[SchemaBase] | None = None
    oneOf: list[SchemaBase] | None = None
    anyOf: list[SchemaBase] | None = None
    not_: SchemaBase | None = Field(None, alias="not")
    items: SchemaBase | None = None
    properties: dict[str, SchemaBase] | None = None
    additionalProperties: dict[str, Any] | bool | None = None


class Contact(BaseModel):
    name: str | None
    url: str | None
    email: str | None


class License(BaseModel):
    name: str
    url: str | None


class Info(BaseModel):
    title: str
    version: str
    description: str | None = None
    termsOfService: str | None = None
    contact: Contact | None = None
    licence: License | None = None


class Reference(BaseModel):
    ref: str = Field(..., alias="$ref")


class Tag(BaseModel):
    name: str
    description: str | None = None
    externalDocs: ExternalDocumentation | None = None


# TODO: Add nats bindings
class NatsBindings(BaseModel):
    pass


class BindingsBase(BaseModel):
    nats: NatsBindings | Reference | None


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
    description: str | None


class MessageTrait(BaseModel):
    headers: Schema | Reference | None
    correlationId: CorrelationId | Reference | None
    schemaFormat: str | None
    contentType: str | None
    name: str | None
    title: str | None
    summary: str | None
    description: str | None
    tags: list[Tag] | None
    externalDocs: ExternalDocumentation | None
    bindings: MessageBindings | Reference | None
    examples: dict[str, Any] | None


class Message(BaseModel):
    headers: Schema | Reference | None = None
    payload: Any | None = None
    correlationId: CorrelationId | Reference | None = None
    schemaFormat: str | None = None
    contentType: str | None = None
    name: str | None = None
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[Tag] | None = None
    externalDocs: ExternalDocumentation | None = None
    bindings: MessageBindings | Reference | None = None
    examples: dict[str, Any] | None = None
    traits: MessageTrait | Reference | None = None


class OperationTrait(BaseModel):
    operationId: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[Tag] | None = None
    externalDocs: ExternalDocumentation | None = None
    bindings: OperationBindings | Reference | None = None


class Operation(BaseModel):
    operationId: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[Tag] | None = None
    externalDocs: ExternalDocumentation | None = None
    bindings: OperationBindings | Reference | None = None
    traits: list[OperationTrait | Reference] | None = None
    message: Message | Reference | None = None


class SubscribeOperation(Operation):
    queue: str | None = Field(None, alias="x-queue")


class RequestOperation(Operation):
    replies: list[Message | Reference] | None = None
    suggestedTimeout: float | None = Field(None, alias="x-suggested-timeout")


class Parameter(BaseModel):
    description: str | None = None
    schema_: dict[str, Any] | Reference = Field(..., alias="schema")
    location: str | None = None


class ChannelItem(BaseModel):
    description: str | None = None
    subscribe: SubscribeOperation | None = None
    publish: Operation | None = None
    request: RequestOperation | None = None
    parameters: dict[str, Parameter | Reference] | None = None
    bindings: ChannelBindings | Reference | None = None
    deprecated: bool | None = None


class ServerVariable(BaseModel):
    enum: list[str] | None = None
    default: str | None = None
    description: str | None = None
    examples: list[str] | None = None


class Server(BaseModel):
    url: str
    protocol: str
    protocolVersion: str | None
    description: str | None
    variables: dict[str, ServerVariable] | None
    bindings: ServerBindings | Reference | None = None


class Components(BaseModel):
    schemas: dict[str, Schema | Reference] | None = None
    messages: dict[str, Message | Reference] | None = None
    parameters: dict[str, dict[str, Parameter] | Reference] | None = None
    correlationIds: dict[str, CorrelationId | Reference] | None = None
    operationTraits: dict[str, OperationTrait | Reference] | None = None
    messageTraits: dict[str, MessageTrait | Reference] | None = None
    serverBindings: dict[str, ServerBindings | Reference] | None = None
    channelBindings: dict[str, ChannelBindings | Reference] | None = None
    operationBindings: dict[str, OperationBindings | Reference] | None = None
    messageBindings: dict[str, MessageBindings | Reference] | None = None


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
    id: str | None = None
    info: Info
    servers: dict[str, Server] | None = None
    defaultContentType: str | None = "application/json"
    channels: dict[str, ChannelItem | Reference] | None = None
    components: Components | None = None
    tags: list[Tag] | None = None
    externalDocs: ExternalDocumentation | None = None
    errors: Errors | None = None
