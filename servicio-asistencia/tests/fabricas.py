"""Funciones para crear datos de prueba sin repetir código en cada archivo."""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.modelos import Sesion

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
