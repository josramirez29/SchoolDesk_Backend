"""Rutas de administración de usuarios. Todas exigen rol ADMIN."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.dependencias import solo_admin
from app.esquemas import UsuarioEdicion, UsuarioNuevo, UsuarioRespuesta
from app.modelos import Usuario
from app.servicios import usuarios
from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("", response_model=list[UsuarioRespuesta])
def listar(
    rol: Rol | None = None,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> list[Usuario]:
    return usuarios.listar_usuarios(sesion, rol)


@router.post("", response_model=UsuarioRespuesta, status_code=201)
def crear(
    datos: UsuarioNuevo,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    return usuarios.crear_usuario(sesion, datos)


@router.get("/{usuario}", response_model=UsuarioRespuesta)
def obtener(
    usuario: str,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    return usuarios.obtener_usuario(sesion, usuario)


@router.patch("/{usuario}", response_model=UsuarioRespuesta)
def editar(
    usuario: str,
    datos: UsuarioEdicion,
    admin: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    return usuarios.editar_usuario(sesion, usuario, datos, quien_edita=admin.usuario)


@router.delete("/{usuario}", response_model=UsuarioRespuesta)
def desactivar(
    usuario: str,
    admin: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    return usuarios.desactivar_usuario(sesion, usuario, quien_desactiva=admin.usuario)
