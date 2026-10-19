"""Administración de cuentas (solo el admin llega aquí)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contrasenas import generar_hash
from app.esquemas import UsuarioEdicion, UsuarioNuevo
from app.modelos import Usuario
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.roles import Rol


def listar_usuarios(sesion: Session, rol: Rol | None = None) -> list[Usuario]:
    consulta = select(Usuario).order_by(Usuario.apellidos, Usuario.nombre)
    if rol is not None:
        consulta = consulta.where(Usuario.rol == rol)
    return list(sesion.scalars(consulta))


def obtener_usuario(sesion: Session, usuario: str) -> Usuario:
    encontrado = sesion.get(Usuario, usuario)
    if encontrado is None:
        raise ErrorApp(404, "USUARIO_NO_ENCONTRADO", f"No existe el usuario {usuario}")
    return encontrado


def crear_usuario(sesion: Session, datos: UsuarioNuevo) -> Usuario:
    if datos.rol == Rol.ALUMNO:
        # Un alumno necesita también su registro académico; si se creara solo
        # la cuenta, quedaría un alumno que puede entrar pero sin materias.
        raise ErrorApp(
            422, "ROL_NO_PERMITIDO", "Las cuentas de alumno se crean al dar de alta al alumno"
        )
    if sesion.get(Usuario, datos.usuario) is not None:
        raise ErrorApp(409, "USUARIO_DUPLICADO", f"Ya existe una cuenta con el usuario {datos.usuario}")
    _validar_email_disponible(sesion, datos.email)

    nuevo = Usuario(
        usuario=datos.usuario,
        nombre=datos.nombre,
        apellidos=datos.apellidos,
        email=datos.email,
        # Contraseña inicial = número de empleado; el usuario la cambia después.
        hash_contrasena=generar_hash(datos.usuario),
        rol=datos.rol,
    )
    sesion.add(nuevo)
    sesion.commit()
    return nuevo


def editar_usuario(sesion: Session, usuario: str, datos: UsuarioEdicion, quien_edita: str) -> Usuario:
    encontrado = obtener_usuario(sesion, usuario)

    if datos.nombre is not None:
        encontrado.nombre = datos.nombre
    if datos.apellidos is not None:
        encontrado.apellidos = datos.apellidos
    if datos.email is not None:
        _validar_email_disponible(sesion, datos.email, excepto=usuario)
        encontrado.email = datos.email
    if datos.activo is not None:
        if not datos.activo:
            _validar_no_es_uno_mismo(usuario, quien_edita)
        encontrado.activo = datos.activo
    if datos.restablecer_contrasena:
        encontrado.hash_contrasena = generar_hash(encontrado.usuario)

    sesion.commit()
    return encontrado


def desactivar_usuario(sesion: Session, usuario: str, quien_desactiva: str) -> Usuario:
    """Baja lógica: la cuenta deja de poder entrar, pero su historial se conserva."""
    encontrado = obtener_usuario(sesion, usuario)
    _validar_no_es_uno_mismo(usuario, quien_desactiva)
    encontrado.activo = False
    sesion.commit()
    return encontrado


def _validar_email_disponible(sesion: Session, email: str, excepto: str | None = None) -> None:
    existente = sesion.scalars(select(Usuario).where(Usuario.email == email)).first()
    if existente is not None and existente.usuario != excepto:
        raise ErrorApp(409, "EMAIL_DUPLICADO", f"El correo {email} ya está registrado")


def _validar_no_es_uno_mismo(usuario: str, quien_hace: str) -> None:
    # Evita que el admin se quede fuera del sistema por accidente.
    if usuario == quien_hace:
        raise ErrorApp(409, "AUTODESACTIVACION", "No puedes desactivar tu propia cuenta")
