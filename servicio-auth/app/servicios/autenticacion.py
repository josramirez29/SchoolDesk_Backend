"""Lógica de autenticación. No sabe nada de HTTP: recibe datos y devuelve datos."""

from sqlalchemy.orm import Session

from app.contrasenas import HASH_FALSO, verificar_contrasena
from app.esquemas import RespuestaLogin, UsuarioRespuesta
from app.modelos import Usuario
from app.tokens import crear_token
from schooldesk_comun.errores import ErrorApp


def _credenciales_invalidas() -> ErrorApp:
    # Mismo mensaje si falla el usuario o la contraseña: así no se puede
    # averiguar qué matrículas existen probando el login.
    return ErrorApp(401, "CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos")


def iniciar_sesion(sesion: Session, usuario: str, contrasena: str) -> RespuestaLogin:
    encontrado = sesion.get(Usuario, usuario)

    if encontrado is None:
        # Se verifica contra un hash falso para que la respuesta tarde lo mismo
        # que con un usuario real; si no, el tiempo delataría qué usuarios existen.
        verificar_contrasena(contrasena, HASH_FALSO)
        raise _credenciales_invalidas()

    if not verificar_contrasena(contrasena, encontrado.hash_contrasena):
        raise _credenciales_invalidas()

    if not encontrado.activo:
        raise ErrorApp(403, "CUENTA_DESACTIVADA", "Tu cuenta está desactivada, contacta al administrador")

    return RespuestaLogin(
        token_acceso=crear_token(encontrado),
        usuario=UsuarioRespuesta.model_validate(encontrado),
    )


def obtener_perfil(sesion: Session, usuario: str) -> Usuario:
    encontrado = sesion.get(Usuario, usuario)
    if encontrado is None:
        raise ErrorApp(404, "USUARIO_NO_ENCONTRADO", "El usuario no existe")
    return encontrado
