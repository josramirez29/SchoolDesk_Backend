"""Funciones para crear datos de prueba sin repetir código en cada archivo.

Usan los mismos datos de datos-ejemplo/ para que las pruebas se parezcan a la demo.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.modelos import Alumno, Materia
from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import ALGORITMO_JWT
from tests.conftest import CLAVE_JWT_PRUEBA


def nuevo_alumno(**cambios: Any) -> Alumno:
    datos: dict[str, Any] = {
        "matricula": "202231045",
        "nombre": "Ana Sofía",
        "apellidos": "Acosta Bravo",
    }
    datos.update(cambios)
    return Alumno(**datos)


def nueva_materia(**cambios: Any) -> Materia:
    datos: dict[str, Any] = {
        "nrc": "48308",
        "clave": "ITIS 702",
        "nombre": "Desarrollo de Sitios Web",
        "seccion": "001",
        "num_empleado_docente": "100521347",
        "nombre_docente": "Laura Méndez Ortega",
    }
    datos.update(cambios)
    return Materia(**datos)


def encabezado_de(
    rol: Rol, usuario: str = "100500001", nombre: str = "Admin SchoolDesk"
) -> dict[str, str]:
    """Header Authorization con un token firmado como lo haría servicio-auth.

    Academic no tiene tabla de usuarios: le basta con validar el token.
    """
    datos = {
        "sub": usuario,
        "nombre": nombre,
        "rol": rol.value,
        "exp": datetime.now(UTC) + timedelta(hours=1),  # dura toda la corrida de pruebas
    }
    token = jwt.encode(datos, CLAVE_JWT_PRUEBA, algorithm=ALGORITMO_JWT)
    return {"Authorization": f"Bearer {token}"}


ADMIN = encabezado_de(Rol.ADMIN)
DOCENTE = encabezado_de(Rol.DOCENTE, usuario="100521347", nombre="Laura Méndez Ortega")
OTRO_DOCENTE = encabezado_de(Rol.DOCENTE, usuario="100534812", nombre="Ricardo Salinas Pérez")
ALUMNO = encabezado_de(Rol.ALUMNO, usuario="202231045", nombre="Ana Sofía Acosta Bravo")
