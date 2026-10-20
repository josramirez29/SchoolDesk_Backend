"""Ruta del alumno para generar su QR de asistencia."""

from datetime import datetime

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy.orm import Session

from app.base_datos import obtener_bd
from app.clientes.academico import ClienteAcademico
from app.dependencias import obtener_cliente_academico, solo_alumno
from app.esquemas import QrGenerado, SolicitudQr
from app.redis_cliente import obtener_redis
from app.reloj import obtener_ahora
from app.servicios import qr
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/qr", tags=["QR"])


@router.post("", response_model=QrGenerado, status_code=201)
def generar(
    datos: SolicitudQr,
    alumno: UsuarioActual = Depends(solo_alumno),
    bd: Session = Depends(obtener_bd),
    redis: Redis = Depends(obtener_redis),
    cliente_academico: ClienteAcademico = Depends(obtener_cliente_academico),
    ahora: datetime = Depends(obtener_ahora),
) -> QrGenerado:
    return qr.generar_qr(bd, redis, cliente_academico, alumno, datos.nrc, ahora)
