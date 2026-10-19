from functools import lru_cache

from pydantic_settings import BaseSettings


class ConfiguracionAuth(BaseSettings):
    """Configuración propia de servicio-auth (se lee del entorno).

    La clave del JWT no está aquí: vive en ConfiguracionComun porque
    todos los servicios la necesitan para validar tokens.
    """

    url_base_datos: str = "postgresql+psycopg://schooldesk:schooldesk@localhost:5432/auth_db"
    minutos_expiracion_token: int = 480  # 8 horas: una jornada escolar


@lru_cache
def obtener_configuracion() -> ConfiguracionAuth:
    return ConfiguracionAuth()
