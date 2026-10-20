from functools import lru_cache

from pydantic_settings import BaseSettings


class ConfiguracionAcademico(BaseSettings):
    """Configuración propia de servicio-academico (se lee del entorno)."""

    url_base_datos: str = "postgresql+psycopg://schooldesk:schooldesk@localhost:5432/academico_db"
    url_servicio_auth: str = "http://localhost:8001"
    url_servicio_asistencia: str = "http://localhost:8003"
    # Si otro servicio no responde en este tiempo, se considera caído.
    segundos_espera_servicios: float = 5.0


@lru_cache
def obtener_configuracion() -> ConfiguracionAcademico:
    return ConfiguracionAcademico()
