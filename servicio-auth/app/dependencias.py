"""Dependencias de FastAPI que usan varias rutas del servicio."""

from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import requerir_roles

solo_admin = requerir_roles(Rol.ADMIN)
