"""Admin inicial: resuelve el problema del huevo y la gallina.

Solo un admin puede crear usuarios, así que en una base vacía nadie podría
entrar nunca. Al arrancar, si la configuración trae un admin inicial y todavía
no existe ningún admin, se crea. Si ya hay uno, no hace nada: reiniciar el
servicio es seguro.
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contrasenas import generar_hash
from app.modelos import Usuario
from schooldesk_comun.roles import Rol


def crear_admin_inicial(sesion: Session, usuario: str, contrasena: str) -> bool:
    """Crea el admin si no hay ninguno. Devuelve True si lo creó."""
    # Se valida aquí (y no con Pydantic) porque estos datos vienen del entorno,
    # no de una petición. Un error aquí detiene el arranque: mejor fallar
    # pronto que arrancar con una contraseña débil.
    if not re.fullmatch(r"\d{9}", usuario):
        raise ValueError("ADMIN_INICIAL_USUARIO debe tener 9 dígitos")
    if len(contrasena) < 8:
        raise ValueError("ADMIN_INICIAL_CONTRASENA debe tener al menos 8 caracteres")

    ya_hay_admin = sesion.scalars(select(Usuario).where(Usuario.rol == Rol.ADMIN)).first()
    if ya_hay_admin is not None:
        return False

    sesion.add(
        Usuario(
            usuario=usuario,
            nombre="Administrador",
            apellidos="SchoolDesk",
            email="admin@schooldesk.example.com",
            hash_contrasena=generar_hash(contrasena),
            rol=Rol.ADMIN,
        )
    )
    sesion.commit()
    return True
