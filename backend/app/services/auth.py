from backend.app.core.errors import AppError
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.repositories import users as users_repo


def register_user(email: str, password: str) -> dict:
    hashed = hash_password(password)
    user = users_repo.create_user(email, hashed)
    token = create_access_token(user["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "created_at": user["created_at"],
        },
    }


def login_user(email: str, password: str) -> dict:
    user = users_repo.get_user_by_email(email)
    if user is None or not verify_password(password, user["hashed_password"]):
        raise AppError(
            "invalid_credentials",
            "Correo o contraseña incorrectos.",
            401,
        )

    token = create_access_token(user["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "created_at": user["created_at"],
        },
    }
