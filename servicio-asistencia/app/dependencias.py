"""Dependencias de FastAPI que usan varias rutas del servicio."""

from functools import lru_cache

from app.clientes.academico import ClienteAcademico
from app.configuracion import obtener_configuracion
from schooldesk_comun.configuracion import obtener_configuracion_comun
from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import requerir_roles

solo_docente = requerir_roles(Rol.DOCENTE)
solo_alumno = requerir_roles(Rol.ALUMNO)


@lru_cache  # un solo cliente para todo el servicio: reutiliza las conexiones abiertas
def obtener_cliente_academico() -> ClienteAcademico:
    configuracion = obtener_configuracion()
    return ClienteAcademico(
        url_base=configuracion.url_servicio_academico,
        clave_interna=obtener_configuracion_comun().clave_interna,
        segundos_espera=configuracion.segundos_espera_servicios,
    )
