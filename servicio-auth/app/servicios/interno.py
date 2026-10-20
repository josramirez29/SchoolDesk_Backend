"""Operaciones que piden otros servicios (servicio-academico)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.esquemas import CuentaNueva, RespuestaLote
from app.modelos import Usuario
from app.servicios.usuarios import (
    emails_en_uso,
    guardar_cuentas_nuevas,
    obtener_usuario,
    usuarios_existentes,
)
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.roles import Rol


def crear_cuentas_de_alumnos(sesion: Session, cuentas: list[CuentaNueva]) -> RespuestaLote:
    """Crea las cuentas de alumnos que falten. Lo llama academic al dar de alta alumnos.

    Es idempotente: las cuentas de alumno que ya existen se omiten. Así, si academic
    falla después de llamar aquí, puede repetir la operación sin duplicar nada.
    """
    _validar_sin_repetidos(cuentas)

    ya_existen = usuarios_existentes(sesion, [cuenta.usuario for cuenta in cuentas])
    con_otro_rol = sorted(
        usuario for usuario, existente in ya_existen.items() if existente.rol != Rol.ALUMNO
    )
    if con_otro_rol:
        raise ErrorApp(
            409,
            "USUARIO_CON_OTRO_ROL",
            "Algunas matrículas ya pertenecen a una cuenta que no es de alumno",
            extra={"usuarios": con_otro_rol},
        )

    nuevas = [cuenta for cuenta in cuentas if cuenta.usuario not in ya_existen]
    emails_ocupados = emails_en_uso(sesion, [cuenta.email for cuenta in nuevas])
    if emails_ocupados:
        # Se devuelven los emails para que academic diga en qué fila está cada uno.
        raise ErrorApp(
            409,
            "EMAIL_EN_USO",
            "Algunos correos ya pertenecen a otra cuenta",
            extra={"emails": sorted(emails_ocupados)},
        )

    guardar_cuentas_nuevas(sesion, nuevas, Rol.ALUMNO)
    return RespuestaLote(
        creados=[cuenta.usuario for cuenta in nuevas],
        omitidos=sorted(ya_existen),
    )


def listar_docentes_activos(sesion: Session) -> list[Usuario]:
    """Para que academic valide que el docente de una materia existe y puede entrar."""
    consulta = (
        select(Usuario)
        .where(Usuario.rol == Rol.DOCENTE, Usuario.activo.is_(True))
        .order_by(Usuario.apellidos, Usuario.nombre)
    )
    return list(sesion.scalars(consulta))


def _validar_sin_repetidos(cuentas: list[CuentaNueva]) -> None:
    usuarios = [cuenta.usuario for cuenta in cuentas]
    emails = [cuenta.email for cuenta in cuentas]
    if len(set(usuarios)) != len(usuarios) or len(set(emails)) != len(emails):
        raise ErrorApp(422, "LOTE_CON_REPETIDOS", "El lote tiene matrículas o correos repetidos")


def actualizar_nombre(sesion: Session, usuario: str, nombre: str, apellidos: str) -> None:
    """Academic llama aquí cuando el admin corrige el nombre de un alumno,
    para que el nombre del token (el que se ve al iniciar sesión) coincida."""
    encontrado = obtener_usuario(sesion, usuario)
    encontrado.nombre = nombre
    encontrado.apellidos = apellidos
    sesion.commit()
