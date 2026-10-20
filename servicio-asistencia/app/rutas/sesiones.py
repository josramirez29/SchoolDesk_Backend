"""Rutas de sesiones de asistencia. Todas exigen rol DOCENTE."""

from datetime import datetime

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy.orm import Session

from app.base_datos import obtener_bd
from app.clientes.academico import ClienteAcademico
from app.dependencias import obtener_cliente_academico, solo_docente
from app.esquemas import Escaneo, RegistroRespuesta, SesionDetalle, SesionNueva, SesionResumen
from app.redis_cliente import obtener_redis
from app.reloj import obtener_ahora
from app.servicios import qr, sesiones
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/sesiones", tags=["Sesiones"])


@router.post("", response_model=SesionDetalle, status_code=201)
def abrir(
    datos: SesionNueva,
    docente: UsuarioActual = Depends(solo_docente),
    bd: Session = Depends(obtener_bd),
    cliente_academico: ClienteAcademico = Depends(obtener_cliente_academico),
    ahora: datetime = Depends(obtener_ahora),
) -> SesionDetalle:
    return sesiones.abrir_sesion(bd, cliente_academico, docente, datos.nrc, ahora)


@router.get("", response_model=list[SesionResumen])
def historial(
    nrc: str,
    docente: UsuarioActual = Depends(solo_docente),
    bd: Session = Depends(obtener_bd),
    ahora: datetime = Depends(obtener_ahora),
) -> list[SesionResumen]:
    return sesiones.listar_sesiones(bd, nrc, docente, ahora)


@router.get("/{sesion_id}", response_model=SesionDetalle)
def detalle(
    sesion_id: int,
    docente: UsuarioActual = Depends(solo_docente),
    bd: Session = Depends(obtener_bd),
    ahora: datetime = Depends(obtener_ahora),
) -> SesionDetalle:
    # El frontend del docente consulta esta ruta cada 3 s para ver la lista en vivo.
    sesion = sesiones.obtener_sesion_del_docente(bd, sesion_id, docente)
    return sesiones.detalle(sesion, ahora)


@router.post("/{sesion_id}/cerrar", response_model=SesionDetalle)
def cerrar(
    sesion_id: int,
    docente: UsuarioActual = Depends(solo_docente),
    bd: Session = Depends(obtener_bd),
    ahora: datetime = Depends(obtener_ahora),
) -> SesionDetalle:
    return sesiones.cerrar_sesion(bd, sesion_id, docente, ahora)


@router.post("/{sesion_id}/escanear", response_model=RegistroRespuesta, status_code=201)
def escanear(
    sesion_id: int,
    datos: Escaneo,
    docente: UsuarioActual = Depends(solo_docente),
    bd: Session = Depends(obtener_bd),
    redis: Redis = Depends(obtener_redis),
    ahora: datetime = Depends(obtener_ahora),
) -> RegistroRespuesta:
    return qr.escanear(bd, redis, docente, sesion_id, datos.token, ahora)
