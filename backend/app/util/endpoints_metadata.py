from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Dict, List, Protocol, Tuple, cast

if TYPE_CHECKING:
    from fastapi import APIRouter


class ModuleRouterInterface(Protocol):
    """
    Protocol that defines the basic structure for a module with a FastAPI router.

    Any module conforming to this protocol must define:
    - A `router` attribute (an instance of `APIRouter`).
    - A `__file__` attribute, which is the file path of the module.
    """

    router: "APIRouter"
    __file__: str


class RouterModule(ModuleRouterInterface, ModuleType):
    """
    A combination of `ModuleType` and `ModuleRouterInterface` protocol.

    This represents a module with an explicitly defined FastAPI `router` and a
    `__file__` attribute, inheriting properties of a standard Python module.
    """

    pass


def process_module_route(
    module_router: ModuleType,
) -> Tuple["APIRouter", Dict[str, str]]:
    """
    Processes a module to extract metadata and its associated FastAPI router.

    Verifies that the module has:
    - A `__file__` attribute to determine the module's file name.
    - A `router` attribute which must be an instance of `APIRouter`.

    Additionally:
    - Derives a name for the module based on its file name, replacing underscores with hyphens.
    - Extracts the module's docstring as the description. If no docstring is present, a default
      description is used.
    - Appends the module name to the router's tags if it hasn't already been added.

    Args:
        module_router: A module containing a FastAPI router.

    Returns:
        A tuple containing:
        - The FastAPI router (`APIRouter`) from the module.
        - A dictionary with metadata about the router, including `name` and `description`.

    Raises:
        AttributeError: If the module lacks a `__file__` or `router` attribute.
    """
    if not hasattr(module_router, "__file__"):
        raise AttributeError(
            f"Module {module_router.__name__} does not define a '__file__'."
        )

    if not hasattr(module_router, "router"):
        raise AttributeError(
            f"Module {module_router.__name__} does not define a 'router'."
        )

    module_router = cast(RouterModule, module_router)
    router = module_router.router
    metadata = {
        "name": Path(module_router.__file__).stem.replace("_", "-"),
        "description": (
            module_router.__doc__.strip()
            if module_router.__doc__
            else "No description provided."
        ),
    }
    tag = metadata["name"]
    if tag not in router.tags:
        router.tags.append(tag)

    return router, metadata


def build_routers_and_metadata(
    route_modules: List[ModuleType],
) -> Tuple[List["APIRouter"], List[Dict[str, str]]]:
    """
    Processes a list of route modules to extract routers and relevant metadata.

    Iterates through each module in the provided list, calling `process_module_route`
    to extract:
    - The FastAPI router (`APIRouter`) defined in the module.
    - Metadata for each router, including its name and description.

    Combines the results from all modules into two lists:
    - A list of `APIRouter` instances.
    - A list of metadata dictionaries for these routers.

    Args:
        route_modules: A list of Python modules, each containing a FastAPI router and metadata.

    Returns:
        A tuple containing:
        - A list of `APIRouter` instances extracted from the provided modules.
        - A list of dictionaries containing metadata (including `name` and `description`) for the routers.

    Example:
        >>> routers, tags_metadata = build_routers_and_metadata([module1, module2])

    """

    tags_metadata: List[Dict[str, str]] = []
    routers: List["APIRouter"] = []
    for mod in route_modules:
        router, metadata = process_module_route(mod)
        tags_metadata.append(metadata)
        routers.append(router)
    return routers, tags_metadata
