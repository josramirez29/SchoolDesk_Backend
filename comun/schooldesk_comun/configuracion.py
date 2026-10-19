from functools import lru_cache

from pydantic_settings import BaseSettings


class ConfiguracionComun(BaseSettings):
    """Configuración que comparten todos los servicios.

    Se lee de las variables de entorno CLAVE_JWT y CLAVE_INTERNA.
    """

    clave_jwt: str
    clave_interna: str


@lru_cache
def obtener_configuracion_comun() -> ConfiguracionComun:
    return ConfiguracionComun()
