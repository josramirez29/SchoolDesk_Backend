"""Rutas internas: solo las llaman otros servicios, con la clave X-Clave-Interna.

El gateway bloquea /interno/*, así que no se pueden llamar desde fuera.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.esquemas import DocenteResumen, RespuestaLote, SolicitudLoteAlumnos
from app.modelos import Usuario
from app.servicios import interno
from schooldesk_comun.interno import requerir_clave_interna

router = APIRouter(
    prefix="/interno",
    tags=["Interno"],
    dependencies=[Depends(requerir_clave_interna)],  # aplica a todas las rutas de aquí
)


@router.post("/usuarios/lote", response_model=RespuestaLote)
def crear_cuentas_de_alumnos(
    datos: SolicitudLoteAlumnos, sesion: Session = Depends(obtener_sesion)
) -> RespuestaLote:
    return interno.crear_cuentas_de_alumnos(sesion, datos.cuentas)


@router.get("/docentes", response_model=list[DocenteResumen])
def listar_docentes(sesion: Session = Depends(obtener_sesion)) -> list[Usuario]:
    return interno.listar_docentes_activos(sesion)
