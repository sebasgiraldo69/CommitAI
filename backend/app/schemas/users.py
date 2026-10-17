import re

from pydantic import Field, field_validator

from backend.app.schemas.commitments import StrictModel

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRegisterRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip().lower()
            if not EMAIL_REGEX.match(value):
                raise ValueError("El formato de correo no es válido.")
            return value
        raise ValueError("El correo debe ser un texto.")


class UserLoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class UserResponse(StrictModel):
    id: str
    email: str
    created_at: str


class TokenResponse(StrictModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
