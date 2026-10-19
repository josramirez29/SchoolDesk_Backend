from collections.abc import Callable
from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from schooldesk_comun.configuracion import obtener_configuracion_comun
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.roles import Rol

ALGORITMO_JWT = "HS256"

esquema_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UsuarioActual:
    """Usuario autenticado, tal como viene en el JWT.

    `usuario` es el identificador estable: la matrícula de un alumno
    o el número de empleado de un docente o admin.
    """

    usuario: str
    nombre: str
    rol: Rol


def decodificar_token(token: str, clave: str) -> UsuarioActual:
    """Valida el JWT localmente (firma y expiración), sin llamar a auth."""
    try:
        datos = jwt.decode(token, clave, algorithms=[ALGORITMO_JWT])
        return UsuarioActual(
            usuario=datos["sub"],
            nombre=datos["nombre"],
            rol=Rol(datos["rol"]),
        )
    except jwt.ExpiredSignatureError:
        raise ErrorApp(401, "TOKEN_EXPIRADO", "La sesión expiró, inicia sesión de nuevo")
    except (jwt.PyJWTError, KeyError, ValueError):
        raise ErrorApp(401, "TOKEN_INVALIDO", "Token inválido")


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
) -> UsuarioActual:
    """Dependencia de FastAPI: exige un JWT válido en el header Authorization."""
    if credenciales is None:
        raise ErrorApp(401, "NO_AUTENTICADO", "Falta el token de autenticación")
    return decodificar_token(credenciales.credentials, obtener_configuracion_comun().clave_jwt)


def requerir_roles(*roles: Rol) -> Callable[..., UsuarioActual]:
    """Crea una dependencia que solo deja pasar a los roles indicados.

    Uso: `usuario: UsuarioActual = Depends(requerir_roles(Rol.ADMIN))`
    """

    def dependencia(usuario: UsuarioActual = Depends(obtener_usuario_actual)) -> UsuarioActual:
        if usuario.rol not in roles:
            raise ErrorApp(403, "SIN_PERMISO", "No tienes permiso para esta acción")
        return usuario

    return dependencia
