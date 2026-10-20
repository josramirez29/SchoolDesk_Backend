"""Dependencias de FastAPI que usan varias rutas del servicio."""

from functools import lru_cache

from app.clientes.auth import ClienteAuth
from app.configuracion import obtener_configuracion
from schooldesk_comun.configuracion import obtener_configuracion_comun
from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import requerir_roles

solo_admin = requerir_roles(Rol.ADMIN)
admin_o_docente = requerir_roles(Rol.ADMIN, Rol.DOCENTE)


@lru_cache  # un solo cliente para todo el servicio: reutiliza las conexiones abiertas
def obtener_cliente_auth() -> ClienteAuth:
    configuracion = obtener_configuracion()
    return ClienteAuth(
        url_base=configuracion.url_servicio_auth,
        clave_interna=obtener_configuracion_comun().clave_interna,
        segundos_espera=configuracion.segundos_espera_servicios,
    )
