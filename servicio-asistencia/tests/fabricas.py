"""Funciones para crear datos de prueba sin repetir código en cada archivo."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.modelos import Sesion
from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import ALGORITMO_JWT
from tests.claves import CLAVE_JWT_PRUEBA

# Hora fija de las pruebas: una clase que empieza a las 9:00 (UTC).
INICIO_CLASE = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


def minutos_despues(minutos: float) -> datetime:
    return INICIO_CLASE + timedelta(minutes=minutos)


def nueva_sesion(**cambios: Any) -> Sesion:
    """Sesión de 10 minutos de Desarrollo de Sitios Web, abierta por Laura a las 9:00."""
    datos: dict[str, Any] = {
        "nrc": "48308",
        "num_empleado_docente": "100521347",
        "iniciada_en": INICIO_CLASE,
        "termina_en": minutos_despues(10),
    }
    datos.update(cambios)
    return Sesion(**datos)


def encabezado_de(rol: Rol, usuario: str, nombre: str) -> dict[str, str]:
    """Header Authorization con un token firmado como lo haría servicio-auth."""
    datos = {
        "sub": usuario,
        "nombre": nombre,
        "rol": rol.value,
        # Expira en una hora REAL: el reloj falso solo afecta a las reglas de
        # asistencia, no a la validación del token.
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(datos, CLAVE_JWT_PRUEBA, algorithm=ALGORITMO_JWT)
    return {"Authorization": f"Bearer {token}"}


DOCENTE = encabezado_de(Rol.DOCENTE, "100521347", "Laura Méndez Ortega")
OTRO_DOCENTE = encabezado_de(Rol.DOCENTE, "100534812", "Ricardo Salinas Pérez")
ALUMNO = encabezado_de(Rol.ALUMNO, "202231045", "Ana Sofía Acosta Bravo")
OTRO_ALUMNO = encabezado_de(Rol.ALUMNO, "202233918", "Bruno Aguilar Campos")
