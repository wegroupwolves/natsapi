from collections import deque
from typing_extensions import Annotated, Literal, get_args, get_origin
from copy import copy
from dataclasses import dataclass, is_dataclass
from natsapi.asyncapi.constants import REF_PREFIX, REF_TEMPLATE
from enum import Enum
from functools import lru_cache
from typing import (
    Any,
    Optional,
    Callable,
    Literal,
    Deque,
    Dict,
    FrozenSet,
    List,
    Mapping,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)
from pydantic import BaseModel, create_model
from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC_VERSION_MINOR_TUPLE = tuple(int(x) for x in PYDANTIC_VERSION.split(".")[:2])
PYDANTIC_V2 = PYDANTIC_VERSION_MINOR_TUPLE[0] == 2

ModelNameMap = Dict[Union[Type[BaseModel], Type[Enum]], str]

if PYDANTIC_V2:
    from pydantic.fields import FieldInfo
    from pydantic import ValidationError as ValidationError
    from pydantic.deprecated.json import ENCODERS_BY_TYPE
    from pydantic_settings import BaseSettings
    from pydantic import RootModel  # noqa
    from pydantic import TypeAdapter

    from pydantic import BaseConfig

    from pydantic_core import PydanticUndefined, PydanticUndefinedType
    from pydantic._internal._utils import lenient_issubclass as lenient_issubclass

    from pydantic.json_schema import GenerateJsonSchema as GenerateJsonSchema
    from pydantic.json_schema import JsonSchemaValue as JsonSchemaValue

    Undefined = PydanticUndefined
    UndefinedType = PydanticUndefinedType

    @dataclass
    class ModelField:
        field_info: FieldInfo
        name: str
        mode: Literal["validation", "serialization"] = "validation"
        # required: bool
        sub_fields: Optional[str] = None
        # type_: Any
        # class_validators: Optional[Dict[str, Any]] = None
        # model_config: Type[BaseConfig] = BaseConfig

        @property
        def alias(self) -> str:
            a = self.field_info.alias
            return a if a is not None else self.name

        @property
        def required(self) -> bool:
            return self.field_info.is_required()

        @property
        def default(self) -> Any:
            return self.get_default()

        @property
        def type_(self) -> Any:
            return self.field_info.annotation

        def __post_init__(self) -> None:
            self._type_adapter: TypeAdapter[Any] = TypeAdapter(Annotated[self.field_info.annotation, self.field_info])

        def get_default(self) -> Any:
            if self.field_info.is_required():
                return Undefined
            return self.field_info.get_default(call_default_factory=True)

        def validate(
            self,
            value: Any,
            values: Dict[str, Any] = {},  # noqa: B006
            *,
            loc: Tuple[Union[int, str], ...] = (),
        ) -> Tuple[Any, Union[List[Dict[str, Any]], None]]:
            try:
                return (
                    self._type_adapter.validate_python(value, from_attributes=True),
                    None,
                )
            except ValidationError as exc:
                return None, _regenerate_error_with_loc(errors=exc.errors(include_url=False), loc_prefix=loc)

        def serialize(
            self,
            value: Any,
            *,
            mode: Literal["json", "python"] = "json",
            by_alias: bool = True,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
        ) -> Any:
            # What calls this code passes a value that already called
            # self._type_adapter.validate_python(value)
            return self._type_adapter.dump_python(
                value,
                mode=mode,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )

        def __hash__(self) -> int:
            # Each ModelField is unique for our purposes, to allow making a dict from
            # ModelField to its JSON Schema.
            return id(self)

    def _normalize_errors(errors: Sequence[Any]) -> List[Dict[str, Any]]:
        return errors  # type: ignore[return-value]

    def get_model_fields(model: Type[BaseModel]) -> List[ModelField]:
        return [ModelField(field_info=field_info, name=name) for name, field_info in model.model_fields.items()]

    def get_compat_model_name_map(fields: List[ModelField]):
        return {}

    def get_definitions(
        *,
        fields: List[ModelField],
        schema_generator: GenerateJsonSchema,
        model_name_map: ModelNameMap,
        separate_input_output_schemas: bool = True,
    ) -> Tuple[
        Dict[Tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
        Dict[str, Dict[str, Any]],
    ]:
        override_mode: Union[Literal["validation"], None] = None if separate_input_output_schemas else "validation"
        inputs = [(field, override_mode or field.mode, field._type_adapter.core_schema) for field in fields]
        field_mapping, definitions = schema_generator.generate_definitions(inputs=inputs)
        return field_mapping, definitions  # type: ignore[return-value]

else:
    from pydantic.json import ENCODERS_BY_TYPE  # noqa: F401
    from pydantic import BaseSettings  # noqa
    from pydantic import BaseModel

    from pydantic.fields import (  # type: ignore[no-redef,attr-defined]
        ModelField as ModelField,  # noqa: F401
    )
    from pydantic.error_wrappers import (  # type: ignore[no-redef]
        ErrorWrapper as ErrorWrapper,  # noqa: F401
    )

    from pydantic.utils import (  # type: ignore[no-redef]
        lenient_issubclass as lenient_issubclass,  # noqa: F401
    )

    from pydantic.schema import (
        field_schema,
        get_flat_models_from_fields,
        get_model_name_map,
        model_process_schema,
    )

    class RootModel(BaseModel):
        __root__: str

    GetJsonSchemaHandler = Any  # type: ignore[assignment,misc]
    JsonSchemaValue = Dict[str, Any]  # type: ignore[misc]
    CoreSchema = Any  # type: ignore[assignment,misc]

    @dataclass
    class GenerateJsonSchema:  # type: ignore[no-redef]
        ref_template: str

    def _normalize_errors(errors: Sequence[Any]) -> List[Dict[str, Any]]:
        use_errors: List[Any] = []
        for error in errors:
            if isinstance(error, ErrorWrapper):
                new_errors = ValidationError(errors=[error]).errors()  # type: ignore[call-arg]
                use_errors.extend(new_errors)
            elif isinstance(error, list):
                use_errors.extend(_normalize_errors(error))
            else:
                use_errors.append(error)
        return use_errors

    def get_model_fields(model: Type[BaseModel]) -> List[ModelField]:
        return list(model.__fields__.values())  # type: ignore[attr-defined]

    def get_compat_model_name_map(fields: List[ModelField]):
        models = get_flat_models_from_fields(fields, known_models=set())
        return get_model_name_map(models)  # type: ignore[no-any-return]

    def get_model_definitions(
        *,
        flat_models: Set[Union[Type[BaseModel], Type[Enum]]],
        model_name_map: Dict[Union[Type[BaseModel], Type[Enum]], str],
    ) -> Dict[str, Any]:
        definitions: Dict[str, Dict[str, Any]] = {}
        for model in flat_models:
            m_schema, m_definitions, m_nested_models = model_process_schema(
                model, model_name_map=model_name_map, ref_prefix=REF_PREFIX
            )
            definitions.update(m_definitions)
            model_name = model_name_map[model]
            if "description" in m_schema:
                m_schema["description"] = m_schema["description"].split("\f")[0]
            definitions[model_name] = m_schema
        return definitions

    def get_definitions(
        *,
        fields: List[ModelField],
        schema_generator: GenerateJsonSchema,
        model_name_map: ModelNameMap,
        separate_input_output_schemas: bool = True,
    ) -> Tuple[
        Dict[Tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
        Dict[str, Dict[str, Any]],
    ]:
        models = get_flat_models_from_fields(fields, known_models=set())
        return {}, get_model_definitions(flat_models=models, model_name_map=model_name_map)


def _regenerate_error_with_loc(
    *, errors: Sequence[Any], loc_prefix: Tuple[Union[str, int], ...]
) -> List[Dict[str, Any]]:
    updated_loc_errors: List[Any] = [
        {**err, "loc": loc_prefix + err.get("loc", ())} for err in _normalize_errors(errors)
    ]

    return updated_loc_errors


@lru_cache
def get_cached_model_fields(model: Type[BaseModel]) -> List[ModelField]:
    return get_model_fields(model)
