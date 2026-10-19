from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorApp(Exception):
    """Error esperado de la aplicación.

    Todos los servicios responden los errores con el mismo formato:
    {"error": "CODIGO", "detalle": "mensaje legible"}
    """

    def __init__(self, codigo_http: int, error: str, detalle: str) -> None:
        super().__init__(detalle)
        self.codigo_http = codigo_http
        self.error = error
        self.detalle = detalle


def _respuesta_error(codigo_http: int, error: str, detalle: str) -> JSONResponse:
    return JSONResponse(status_code=codigo_http, content={"error": error, "detalle": detalle})


def registrar_manejadores_errores(app: FastAPI) -> None:
    """Hace que cualquier error del servicio salga con el formato común."""

    @app.exception_handler(ErrorApp)
    async def manejar_error_app(_: Request, exc: ErrorApp) -> JSONResponse:
        return _respuesta_error(exc.codigo_http, exc.error, exc.detalle)

    @app.exception_handler(RequestValidationError)
    async def manejar_error_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        mensajes = [
            f"{'.'.join(str(parte) for parte in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return _respuesta_error(422, "VALIDACION", "; ".join(mensajes))

    @app.exception_handler(StarletteHTTPException)
    async def manejar_error_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _respuesta_error(exc.status_code, "ERROR_HTTP", str(exc.detail))
