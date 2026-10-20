"""Rutas de calificaciones de una materia (admin o docente titular)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.dependencias import admin_o_docente
from app.esquemas import CalificacionEntrada, Concentrado
from app.servicios import calificaciones
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/materias/{nrc}/calificaciones", tags=["Calificaciones"])


@router.get("", response_model=Concentrado)
def concentrado(
    nrc: str,
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> Concentrado:
    return calificaciones.obtener_concentrado(sesion, nrc, usuario)


@router.put("", response_model=Concentrado)
def capturar(
    nrc: str,
    entradas: list[CalificacionEntrada],
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> Concentrado:
    return calificaciones.capturar_calificaciones(sesion, nrc, usuario, entradas)
