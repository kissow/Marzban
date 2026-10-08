"""Main business-core billing settings, independent of Node and relay settings."""
from decimal import Decimal
from pydantic import BaseModel, FiniteFloat, Field, field_validator


class MainUsageSettings(BaseModel):
    usage_coefficient: FiniteFloat = Field(gt=0, le=1000)

    @field_validator("usage_coefficient", mode="before")
    @classmethod
    def reject_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("usage_coefficient must be a number, not a boolean")
        return value

    @field_validator("usage_coefficient")
    @classmethod
    def check_precision(cls, value):
        if Decimal(str(value)).normalize().as_tuple().exponent < -5:
            raise ValueError("usage_coefficient allows at most five decimal places")
        return value
