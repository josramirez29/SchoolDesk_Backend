from functools import lru_cache

from pydantic_settings import BaseSettings


class ConfiguracionGateway(BaseSettings):
    """Configuración del gateway (se lee del entorno)."""

    url_servicio_auth: str = "http://localhost:8001"
    url_servicio_academico: str = "http://localhost:8002"
    url_servicio_asistencia: str = "http://localhost:8003"

    # Orígenes desde los que el navegador puede llamar a la API (el frontend de Angular).
    # En el entorno se escribe como lista JSON: ORIGENES_PERMITIDOS='["http://localhost:4200"]'
    origenes_permitidos: list[str] = ["http://localhost:4200"]

    # Generoso a propósito: importar 2,000 alumnos crea 2,000 hashes de bcrypt.
    segundos_espera: float = 60.0

    def url_de(self, servicio: str) -> str | None:
        """URL base del servicio por su nombre en la ruta (/api/{servicio}/...)."""
        return {
            "auth": self.url_servicio_auth,
            "academico": self.url_servicio_academico,
            "asistencia": self.url_servicio_asistencia,
        }.get(servicio)


@lru_cache
def obtener_configuracion() -> ConfiguracionGateway:
    return ConfiguracionGateway()
