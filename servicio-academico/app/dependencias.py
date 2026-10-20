"""Dependencias de FastAPI que usan varias rutas del servicio."""

from functools import lru_cache

from app.clientes.asistencia import ClienteAsistencia
from app.clientes.auth import ClienteAuth
from app.configuracion import obtener_configuracion
from schooldesk_comun.configuracion import obtener_configuracion_comun
from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import requerir_roles

solo_admin = requerir_roles(Rol.ADMIN)
admin_o_docente = requerir_roles(Rol.ADMIN, Rol.DOCENTE)
solo_alumno = requerir_roles(Rol.ALUMNO)


# Un solo cliente por servicio destino: httpx reutiliza las conexiones abiertas.


@lru_cache
def obtener_cliente_auth() -> ClienteAuth:
    configuracion = obtener_configuracion()
    return ClienteAuth(
        url_base=configuracion.url_servicio_auth,
        clave_interna=obtener_configuracion_comun().clave_interna,
        segundos_espera=configuracion.segundos_espera_servicios,
    )


@lru_cache
def obtener_cliente_asistencia() -> ClienteAsistencia:
    configuracion = obtener_configuracion()
    return ClienteAsistencia(
        url_base=configuracion.url_servicio_asistencia,
        clave_interna=obtener_configuracion_comun().clave_interna,
        segundos_espera=configuracion.segundos_espera_servicios,
    )
