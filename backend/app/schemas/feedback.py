import re

from pydantic import BaseModel, Field, field_validator


class FeedbackCreate(BaseModel):
    message: str = Field(..., min_length=10, max_length=2000)
    email: str | None = Field(None, max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        # Basic email format validation
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v


class FeedbackResponse(BaseModel):
    success: bool
    message: str
