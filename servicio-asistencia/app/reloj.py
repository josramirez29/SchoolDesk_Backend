"""La hora actual, como dependencia que se puede reemplazar.

Las reglas de asistencia dependen del tiempo (≤ 5 min PRESENTE, sesión de 10 min).
Si el código llamara directamente a datetime.now(), probar un RETARDO obligaría
a esperar 5 minutos reales. Como la hora llega como dependencia, una prueba puede
decir "ahora son las 9:07" y verificar el resultado al instante.
"""

from datetime import UTC, datetime


def obtener_ahora() -> datetime:
    """Dependencia de FastAPI: la hora actual en UTC."""
    return datetime.now(UTC)
