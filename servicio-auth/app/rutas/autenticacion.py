"""Rutas de autenticación. Solo reciben la petición, llaman al servicio y responden."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.esquemas import RespuestaLogin, SolicitudLogin, UsuarioRespuesta
from app.modelos import Usuario
from app.servicios import autenticacion
from schooldesk_comun.seguridad import UsuarioActual, obtener_usuario_actual

router = APIRouter(tags=["Autenticación"])


@router.post("/login", response_model=RespuestaLogin)
def login(datos: SolicitudLogin, sesion: Session = Depends(obtener_sesion)) -> RespuestaLogin:
    return autenticacion.iniciar_sesion(sesion, datos.usuario, datos.contrasena)


@router.get("/perfil", response_model=UsuarioRespuesta)
def perfil(
    actual: UsuarioActual = Depends(obtener_usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    return autenticacion.obtener_perfil(sesion, actual.usuario)
