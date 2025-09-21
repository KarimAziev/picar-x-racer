from copy import deepcopy
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

T = TypeVar("T", bound="BaseModel")


def partial_model(model: Type[T]) -> Type[T]:
    """
    Create a new Pydantic model in which all fields of the given model are optional.

    Metadata attached to the Pydantic fields will remain unchanged, except for
    the addition of the `Optional` type wrapper.

    Example:

    ```python
    from pydantic import BaseModel

    class User(BaseModel):
        id: int
        name: str
        age: int

    PartialUser = partial_model(User)

    partial_user = PartialUser(name="Alice")
    print(partial_user.dict())  # Output: {'id': None, 'name': 'Alice', 'age': None}
    ```

    Example with decorator:

    ```python
    class User(BaseModel):
        id: int
        name: str
        age: int


    @partial_model
    class PartialUser(User):
        pass


    partial_user = PartialUser(name="Alice")
    print(partial_user.dict())  # Output: {'id': None, 'name': 'Alice', 'age': None}
    ```

    """

    def make_field_optional(
        field: FieldInfo, default: Any = None
    ) -> Tuple[Any, FieldInfo]:
        new = deepcopy(field)
        new.default = default
        new.annotation = Optional[field.annotation]  # type: ignore
        return new.annotation, new

    return create_model(
        f"Partial{model.__name__}",
        __base__=model,
        __module__=model.__module__,
        **{
            field_name: make_field_optional(field_info)
            for field_name, field_info in model.model_fields.items()
        },  # type: ignore
    )


def schema_to_dynamic_json(schema: Type[BaseModel]) -> Dict[str, Any]:
    """
    Dynamically generates a JSON-like schema representation of a Pydantic model.

    Args:
        schema: A Pydantic model class (not an instance).

    Returns:
        A representation of the schema as a JSON-like object.
    """

    def extract_fields(model: Type[BaseModel]) -> Dict[str, Any]:
        fields = {}
        for name, field in model.model_fields.items():
            field_props = {
                "type": type_hint_to_json(field.annotation),
                "label": humanize_name(name),
                "description": field.description,
                "examples": field.examples or [],
            }

            if get_origin(field.annotation) is Literal:
                field_props["options"] = list(get_args(field.annotation))

            elif field.annotation is not None and is_enum(field.annotation):
                enum_cls = field.annotation
                options = [member.value for member in cast(Type[Enum], enum_cls)]
                field_props["options"] = options

            fields[name] = field_props
        return fields

    def type_hint_to_json(type_hint: Any) -> Optional[Union[str, List[str]]]:
        if type_hint is None:
            return None
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        if origin is Union:
            return [type_to_json(arg) for arg in args if arg is not type(None)]
        if is_enum(type_hint):
            return "enum"
        if origin is Literal:
            return "literal"
        return type_to_json(type_hint)

    def type_to_json(type_: Any) -> str:

        if type_ is int:
            return "int"
        elif type_ is Literal:
            return "literal"
        elif type_ is str:
            return "str"
        elif type_ is float:
            return "float"
        elif type_ is list:
            return "list"
        elif is_enum(type_):
            return "enum"
        else:
            return str(type_)

    def is_enum(type_: Any) -> bool:
        return isinstance(type_, type) and issubclass(type_, Enum)

    def humanize_name(name: str) -> str:
        return " ".join(word.capitalize() for word in name.split("_"))

    json_schema = {}

    for key, field in schema.model_fields.items():
        model = field.annotation
        if isinstance(model, type) and issubclass(model, BaseModel):
            json_schema[key] = extract_fields(model)

    return json_schema
