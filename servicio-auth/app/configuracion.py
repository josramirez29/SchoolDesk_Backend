from functools import lru_cache

from pydantic_settings import BaseSettings


class ConfiguracionAuth(BaseSettings):
    """Configuración propia de servicio-auth (se lee del entorno).

    La clave del JWT no está aquí: vive en ConfiguracionComun porque
    todos los servicios la necesitan para validar tokens.
    """

    url_base_datos: str = "postgresql+psycopg://schooldesk:schooldesk@localhost:5432/auth_db"
    minutos_expiracion_token: int = 480  # 8 horas: una jornada escolar
    # Costo de bcrypt: cada ronda más duplica el tiempo. 12 es el valor seguro;
    # las pruebas usan 4 (el mínimo) para no tardar minutos.
    rondas_bcrypt: int = 12

    # Admin que se crea al arrancar si todavía no existe ninguno (ver servicios/admin_inicial.py).
    # Sin él no habría forma de entrar: solo un admin puede crear usuarios.
    admin_inicial_usuario: str | None = None
    admin_inicial_contrasena: str | None = None


@lru_cache
def obtener_configuracion() -> ConfiguracionAuth:
    return ConfiguracionAuth()
