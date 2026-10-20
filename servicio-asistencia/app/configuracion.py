from functools import lru_cache

from pydantic_settings import BaseSettings


class ConfiguracionAsistencia(BaseSettings):
    """Configuración propia de servicio-asistencia (se lee del entorno)."""

    url_base_datos: str = "postgresql+psycopg://schooldesk:schooldesk@localhost:5432/asistencia_db"
    url_redis: str = "redis://localhost:6379/0"
    url_servicio_academico: str = "http://localhost:8002"
    segundos_espera_servicios: float = 5.0

    # Reglas de la sesión. En la demo se pueden bajar para no esperar 10 minutos.
    minutos_sesion: int = 10
    minutos_tolerancia: int = 5  # hasta aquí es PRESENTE; después, RETARDO
    segundos_vida_qr: int = 30


@lru_cache
def obtener_configuracion() -> ConfiguracionAsistencia:
    return ConfiguracionAsistencia()
