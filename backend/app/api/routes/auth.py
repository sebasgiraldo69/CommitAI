from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from backend.app.api.deps import get_current_user
from backend.app.schemas.users import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from backend.app.services import auth as service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserRegisterRequest):
    result = service.register_user(payload.email, payload.password)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=result)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest):
    return service.login_user(payload.email, payload.password)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user
