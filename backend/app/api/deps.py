from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from backend.app.core.errors import AppError
from backend.app.core.security import decode_access_token
from backend.app.repositories import users as users_repo

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> dict:
    if not token:
        raise AppError(
            "unauthorized",
            "Se requiere iniciar sesión para realizar esta acción.",
            401,
        )

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AppError(
            "token_invalid",
            "Token no válido.",
            401,
        )

    user = users_repo.get_user_by_id(user_id)
    if user is None:
        raise AppError(
            "user_not_found",
            "El usuario asociado al token no existe.",
            401,
        )

    return {
        "id": user["id"],
        "email": user["email"],
        "created_at": user["created_at"],
    }
