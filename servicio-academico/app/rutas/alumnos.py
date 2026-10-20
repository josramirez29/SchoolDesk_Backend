"""Rutas de alumnos. Todas exigen rol ADMIN."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.clientes.auth import ClienteAuth
from app.dependencias import obtener_cliente_auth, solo_admin
from app.esquemas import AlumnoDetalle, AlumnoEdicion, AlumnoNuevo, AlumnoRespuesta
from app.modelos import Alumno
from app.servicios import alumnos
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/alumnos", tags=["Alumnos"])


@router.get("", response_model=list[AlumnoRespuesta])
def buscar(
    buscar: str | None = None,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> list[Alumno]:
    return alumnos.buscar_alumnos(sesion, buscar)


@router.post("", response_model=AlumnoRespuesta, status_code=201)
def crear(
    datos: AlumnoNuevo,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
    cliente_auth: ClienteAuth = Depends(obtener_cliente_auth),
) -> Alumno:
    return alumnos.crear_alumno(sesion, cliente_auth, datos)


@router.get("/{matricula}", response_model=AlumnoDetalle)
def obtener(
    matricula: str,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> AlumnoDetalle:
    return alumnos.obtener_detalle(sesion, matricula)


@router.patch("/{matricula}", response_model=AlumnoRespuesta)
def editar(
    matricula: str,
    datos: AlumnoEdicion,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
    cliente_auth: ClienteAuth = Depends(obtener_cliente_auth),
) -> Alumno:
    return alumnos.editar_alumno(sesion, cliente_auth, matricula, datos)
