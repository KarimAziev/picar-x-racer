from copy import deepcopy
from typing import Any, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

T = TypeVar("T", bound="BaseModel")


def partial_model(model: Type[BaseModel]):
    def make_field_optional(
        field: FieldInfo, default: Any = None
    ) -> Tuple[Any, FieldInfo]:
        new = deepcopy(field)
        new.default = default
        new.annotation = Optional[field.annotation]  # type: ignore
        return new.annotation, new

    return create_model(
        f'Partial{model.__name__}',
        __base__=model,
        __module__=model.__module__,
        **{
            field_name: make_field_optional(field_info)
            for field_name, field_info in model.model_fields.items()
        },  # type: ignore
    )


# def partial_model(
#     include: Optional[list[str]] = None, exclude: Optional[list[str]] = None
# ) -> Callable[[type[T]], type[T]]:
#     """Return a decorator to make model fields optional"""

#     if exclude is None:
#         exclude = []

#     def decorator(model: type[T]) -> type[T]:
#         def make_optional(
#             field: FieldInfo, default: Any = None
#         ) -> tuple[Any, FieldInfo]:
#             new = deepcopy(field)
#             new.default = default
#             new.annotation = field.annotation
#             return new.annotation, new

#         fields = model.model_fields
#         if include is None:
#             fields = fields.items()
#         else:
#             fields = ((k, v) for k, v in fields.items() if k in include)

#         return create_model(
#             model.__name__,
#             __base__=model,
#             __module__=model.__module__,
#             **{
#                 field_name: make_optional(field_info)
#                 for field_name, field_info in fields
#                 if exclude is None or field_name not in exclude
#             },  # type: ignore
#         )

#     return decorator
