from typing import Annotated, List, Optional

from pydantic import BaseModel, Field


class ShutdownResponse(BaseModel):
    """
    This model indicates whether all robot services have been successfully shut down, and optionally
    provides error messages if any service encountered an issue during shutdown.
    """

    success: Annotated[
        bool,
        Field(
            ...,
            description="Specifies whether all services were gracefuly stopped",
            examples=[True, False],
        ),
    ]
    errors: Annotated[
        Optional[List[str]],
        Field(
            ...,
            description="Optional list of error messages encountered during shutdown, if any service failed to stop properly.",
            examples=[
                ["Failed to shutdown battery service"],
                ["Motor control timeout", "Distance sensor error"],
            ],
        ),
    ] = None
