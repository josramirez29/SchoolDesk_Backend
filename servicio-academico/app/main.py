from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import modelos  # noqa: F401  (registra las tablas en Base.metadata)
from app.base_datos import Base, motor
from app.rutas import (
    alumnos,
    calificaciones,
    importacion,
    interno,
    materias,
    mis_materias,
    ponderaciones,
    reportes,
)
from schooldesk_comun.errores import registrar_manejadores_errores


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    # Crea las tablas que falten al arrancar. Suficiente para la demo;
    # en producción se usarían migraciones (Alembic).
    Base.metadata.create_all(motor)
    yield


app = FastAPI(title="SchoolDesk · servicio-academico", lifespan=ciclo_de_vida)
registrar_manejadores_errores(app)
app.include_router(alumnos.router)
app.include_router(materias.router)
app.include_router(ponderaciones.router)
app.include_router(calificaciones.router)
app.include_router(mis_materias.router)
app.include_router(importacion.router)
app.include_router(reportes.router)
app.include_router(interno.router)


@app.get("/salud", tags=["Salud"])
def salud() -> dict[str, str]:
    return {"estado": "ok"}
