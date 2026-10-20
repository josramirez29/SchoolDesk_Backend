"""Rutas de importación masiva por CSV (solo ADMIN, salvo las plantillas)."""

from typing import Literal

from fastapi import APIRouter, Depends, Response, UploadFile
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.clientes.auth import ClienteAuth
from app.dependencias import obtener_cliente_auth, solo_admin
from app.esquemas import COLUMNAS_ALUMNOS, COLUMNAS_INSCRIPCIONES, COLUMNAS_MATERIAS
from app.servicios import importacion
from schooldesk_comun.importacion import (
    TAMANO_MAXIMO_BYTES,
    ResultadoImportacion,
    respuesta_plantilla,
)
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/importar", tags=["Importación"])

COLUMNAS_POR_TIPO = {
    "alumnos": COLUMNAS_ALUMNOS,
    "materias": COLUMNAS_MATERIAS,
    "inscripciones": COLUMNAS_INSCRIPCIONES,
}


@router.get("/{tipo}/plantilla")
def plantilla(tipo: Literal["alumnos", "materias", "inscripciones"]) -> Response:
    # Pública a propósito: solo trae los encabezados, no datos.
    return respuesta_plantilla(COLUMNAS_POR_TIPO[tipo], f"{tipo}.csv")


@router.post("/alumnos", response_model=ResultadoImportacion)
def importar_alumnos(
    archivo: UploadFile,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
    cliente_auth: ClienteAuth = Depends(obtener_cliente_auth),
) -> ResultadoImportacion:
    return importacion.importar_alumnos(sesion, cliente_auth, _leer(archivo))


@router.post("/materias", response_model=ResultadoImportacion)
def importar_materias(
    archivo: UploadFile,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
    cliente_auth: ClienteAuth = Depends(obtener_cliente_auth),
) -> ResultadoImportacion:
    return importacion.importar_materias(sesion, cliente_auth, _leer(archivo))


@router.post("/inscripciones", response_model=ResultadoImportacion)
def importar_inscripciones(
    archivo: UploadFile,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> ResultadoImportacion:
    return importacion.importar_inscripciones(sesion, _leer(archivo))


def _leer(archivo: UploadFile) -> bytes:
    # Un byte más del límite: así se detecta un archivo demasiado grande
    # sin cargarlo completo en memoria.
    return archivo.file.read(TAMANO_MAXIMO_BYTES + 1)
