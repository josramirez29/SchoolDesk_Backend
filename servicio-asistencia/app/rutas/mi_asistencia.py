"""Ruta del alumno para consultar su asistencia. Usa la matrícula del token."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_bd
from app.clientes.academico import ClienteAcademico
from app.dependencias import obtener_cliente_academico, solo_alumno
from app.esquemas import MiAsistencia
from app.reloj import obtener_ahora
from app.servicios import mi_asistencia
from schooldesk_comun.seguridad import UsuarioActual
from schooldesk_comun.tipos import Nrc

router = APIRouter(prefix="/mi-asistencia", tags=["Alumno"])


@router.get("", response_model=MiAsistencia)
def consultar(
    nrc: Nrc,
    alumno: UsuarioActual = Depends(solo_alumno),
    bd: Session = Depends(obtener_bd),
    cliente_academico: ClienteAcademico = Depends(obtener_cliente_academico),
    ahora: datetime = Depends(obtener_ahora),
) -> MiAsistencia:
    return mi_asistencia.obtener_mi_asistencia(bd, cliente_academico, alumno.usuario, nrc, ahora)
