"""Rutas internas: solo las llama servicio-academico, con la clave X-Clave-Interna.

El gateway bloquea /interno/*, así que no se pueden llamar desde fuera.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_bd
from app.esquemas import ResumenMateria
from app.reloj import obtener_ahora
from app.servicios import interno
from schooldesk_comun.interno import requerir_clave_interna

router = APIRouter(
    prefix="/interno",
    tags=["Interno"],
    dependencies=[Depends(requerir_clave_interna)],  # aplica a todas las rutas de aquí
)


@router.get("/materias/{nrc}/resumen", response_model=ResumenMateria)
def resumen(
    nrc: str,
    bd: Session = Depends(obtener_bd),
    ahora: datetime = Depends(obtener_ahora),
) -> ResumenMateria:
    return interno.resumen_de_materia(bd, nrc, ahora)
