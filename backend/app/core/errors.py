from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
            },
            "request_id": getattr(request.state, "request_id", None),
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def application_error(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        return error_response(
            request,
            exc.status_code,
            exc.code,
            exc.message,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # No devolver el valor recibido: podría contener datos sensibles.
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": "Valor ausente o inválido.",
            }
            for error in exc.errors()
        ]

        return error_response(
            request,
            422,
            "validation_error",
            "Revisa los campos enviados.",
            details,
        )

    @app.exception_handler(HTTPException)
    async def http_error(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = (
            "El recurso solicitado no existe."
            if exc.status_code == 404
            else "No se pudo procesar la solicitud."
        )

        response = error_response(
            request,
            exc.status_code,
            code,
            message,
        )
        if exc.headers:
            response.headers.update(exc.headers)

        return response