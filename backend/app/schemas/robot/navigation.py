"""Navigation policy and measured body envelope, separate from wheelbase."""

import math
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self


class NavigationConfig(BaseModel):
    """Forward-route preference and an optional measured body envelope about the rear axle. Changes require backend restart."""

    model_config = ConfigDict(title="Navigation body envelope and routing")
    prefer_forward: bool = Field(
        default=True,
        title="Prefer forward routes",
        description="Try a bounded forward-only turning search before permitting reverse recovery. Requires backend restart.",
    )
    forward_search_nodes: int = Field(
        default=3000,
        ge=100,
        le=20000,
        title="Forward search budget",
        description="Maximum Hybrid A* expansions spent finding a forward-only route before reverse is allowed.",
    )
    use_body_clearance: bool = Field(
        default=False,
        title="Use measured body envelope",
        description="Use a conservative circle enclosing the body about the rear axle for planning and simulation collisions. Requires all body measurements and a backend restart.",
    )
    body_length_m: Optional[float] = Field(
        default=None,
        gt=0,
        le=3,
        allow_inf_nan=False,
        title="Overall body length",
        json_schema_extra={"props": {"step": 0.01, "suffix": " m"}},
        description="Frontmost to rearmost extent in metres, including equipment. This is NOT the axle-to-axle wheelbase; 57 cm is 0.57 m.",
    )
    body_width_m: Optional[float] = Field(
        default=None,
        gt=0,
        le=3,
        allow_inf_nan=False,
        title="Overall body width",
        json_schema_extra={"props": {"step": 0.01, "suffix": " m"}},
        description="Maximum centered width in metres, including wheels, suspension, and equipment. For an asymmetric body, use twice the larger lateral extent from the centerline.",
    )
    rear_overhang_m: Optional[float] = Field(
        default=None,
        ge=0,
        le=3,
        allow_inf_nan=False,
        title="Rear axle to rear end",
        json_schema_extra={"props": {"step": 0.01, "suffix": " m"}},
        description="Distance from the rear axle center to the rearmost body point. The odometry reference is the rear axle, not the body center.",
    )

    @model_validator(mode="after")
    def validate_envelope(self) -> Self:
        if self.use_body_clearance and any(
            value is None
            for value in (self.body_length_m, self.body_width_m, self.rear_overhang_m)
        ):
            raise ValueError("body clearance requires length, width, and rear overhang")
        if (
            self.rear_overhang_m is not None
            and self.body_length_m is not None
            and self.rear_overhang_m >= self.body_length_m
        ):
            raise ValueError("rear overhang must be smaller than overall length")
        return self

    @property
    def body_radius_m(self) -> float:
        if not self.use_body_clearance:
            return 0.0
        assert (
            self.body_length_m is not None
            and self.body_width_m is not None
            and self.rear_overhang_m is not None
        )
        return math.hypot(
            max(self.rear_overhang_m, self.body_length_m - self.rear_overhang_m),
            self.body_width_m / 2,
        )
