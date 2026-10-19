"""Rutas de importación masiva por CSV."""

from fastapi import APIRouter, Depends, Response, UploadFile
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.dependencias import solo_admin
from app.esquemas import COLUMNAS_DOCENTES
from app.servicios import importacion
from schooldesk_comun.importacion import (
    TAMANO_MAXIMO_BYTES,
    ResultadoImportacion,
    respuesta_plantilla,
)
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/importar", tags=["Importación"])


@router.get("/docentes/plantilla")
def plantilla_docentes() -> Response:
    # Pública a propósito: solo trae los encabezados, no datos.
    return respuesta_plantilla(COLUMNAS_DOCENTES, "docentes.csv")


@router.post("/docentes", response_model=ResultadoImportacion)
def importar_docentes(
    archivo: UploadFile,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> ResultadoImportacion:
    # Se lee un byte más del límite: así se detecta un archivo demasiado grande
    # sin cargarlo completo en memoria.
    contenido = archivo.file.read(TAMANO_MAXIMO_BYTES + 1)
    return importacion.importar_docentes(sesion, contenido)
