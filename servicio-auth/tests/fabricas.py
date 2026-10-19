"""Funciones para crear datos de prueba sin repetir código en cada archivo."""

from typing import Any

from app.contrasenas import generar_hash
from app.modelos import Usuario
from app.tokens import crear_token
from schooldesk_comun.roles import Rol

CONTRASENA_PRUEBA = "contrasena-segura-123"


def nuevo_usuario(**cambios: Any) -> Usuario:
    """Usuario docente válido; `cambios` sobrescribe los campos que la prueba necesite."""
    datos: dict[str, Any] = {
        "usuario": "100521347",
        "nombre": "Laura",
        "apellidos": "Méndez Ortega",
        "email": "laura.mendez@docente.example.com",
        "hash_contrasena": generar_hash(CONTRASENA_PRUEBA),
        "rol": Rol.DOCENTE,
    }
    datos.update(cambios)
    return Usuario(**datos)


def encabezado_de(usuario: Usuario) -> dict[str, str]:
    """Header Authorization con un token válido para ese usuario."""
    return {"Authorization": f"Bearer {crear_token(usuario)}"}
