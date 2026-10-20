import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import modelos  # noqa: F401  (registra las tablas en Base.metadata)
from app.base_datos import Base, FabricaSesiones, motor
from app.configuracion import obtener_configuracion
from app.rutas import autenticacion, importacion, interno, usuarios
from app.servicios.admin_inicial import crear_admin_inicial
from schooldesk_comun.errores import registrar_manejadores_errores

logger = logging.getLogger("uvicorn.error")  # el logger que uvicorn ya muestra en consola


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    # Crea las tablas que falten al arrancar. Suficiente para la demo;
    # en producción se usarían migraciones (Alembic).
    Base.metadata.create_all(motor)

    configuracion = obtener_configuracion()
    if configuracion.admin_inicial_usuario and configuracion.admin_inicial_contrasena:
        with FabricaSesiones() as sesion:
            creado = crear_admin_inicial(
                sesion, configuracion.admin_inicial_usuario, configuracion.admin_inicial_contrasena
            )
        if creado:
            logger.info("Admin inicial creado: %s", configuracion.admin_inicial_usuario)
    yield


app = FastAPI(title="SchoolDesk · servicio-auth", lifespan=ciclo_de_vida)
registrar_manejadores_errores(app)
app.include_router(autenticacion.router)
app.include_router(usuarios.router)
app.include_router(importacion.router)
app.include_router(interno.router)


@app.get("/salud", tags=["Salud"])
def salud() -> dict[str, str]:
    return {"estado": "ok"}
