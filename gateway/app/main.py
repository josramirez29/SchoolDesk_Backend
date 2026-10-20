"""API Gateway: punto de entrada único del backend.

    /api/auth/...        → servicio-auth
    /api/academico/...   → servicio-academico
    /api/asistencia/...  → servicio-asistencia

Es la única parte asíncrona del proyecto: no hace más que esperar respuestas de
otros servicios, y con async un solo proceso atiende muchas esperas a la vez.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.configuracion import obtener_configuracion
from app.proxy import reenviar
from schooldesk_comun.errores import ErrorApp, registrar_manejadores_errores

SERVICIOS = ("auth", "academico", "asistencia")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    # Un solo cliente HTTP para todo el gateway: reutiliza las conexiones abiertas.
    app.state.http = httpx.AsyncClient(timeout=obtener_configuracion().segundos_espera)
    yield
    await app.state.http.aclose()


def obtener_cliente_http(peticion: Request) -> httpx.AsyncClient:
    """Dependencia de FastAPI; las pruebas la reemplazan por un cliente con respuestas simuladas."""
    return peticion.app.state.http


app = FastAPI(title="SchoolDesk · gateway", lifespan=ciclo_de_vida)
registrar_manejadores_errores(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=obtener_configuracion().origenes_permitidos,
    allow_methods=["*"],
    allow_headers=["*"],
    # El token viaja en el header Authorization, no en cookies: no hacen falta credenciales.
    allow_credentials=False,
    # Para que el frontend lea el nombre del archivo al descargar plantillas CSV.
    expose_headers=["Content-Disposition"],
)


@app.get("/salud", tags=["Salud"])
def salud() -> dict[str, str]:
    return {"estado": "ok"}


@app.get("/salud/servicios", tags=["Salud"])
async def salud_de_los_servicios(
    cliente: httpx.AsyncClient = Depends(obtener_cliente_http),
) -> dict[str, str]:
    """Pregunta a los 3 servicios a la vez (no uno tras otro) si están vivos."""

    async def revisar(servicio: str) -> str:
        try:
            url = obtener_configuracion().url_de(servicio)
            respuesta = await cliente.get(f"{url}/salud", timeout=2)
            return "ok" if respuesta.is_success else "con_errores"
        except httpx.HTTPError:
            return "caido"

    estados = await asyncio.gather(*(revisar(servicio) for servicio in SERVICIOS))
    return dict(zip(SERVICIOS, estados, strict=True))


@app.api_route(
    "/api/{servicio}/{ruta:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def proxy(
    servicio: str,
    ruta: str,
    peticion: Request,
    cliente: httpx.AsyncClient = Depends(obtener_cliente_http),
) -> Response:
    url_base = obtener_configuracion().url_de(servicio)
    if url_base is None:
        raise ErrorApp(404, "SERVICIO_DESCONOCIDO", f"No existe el servicio '{servicio}'")
    return await reenviar(cliente, servicio, url_base, ruta, peticion)
