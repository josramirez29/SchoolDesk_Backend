"""Conexión a Redis, donde viven los tokens de QR (duran segundos y se usan una vez)."""

from functools import lru_cache

from redis import Redis

from app.configuracion import obtener_configuracion


@lru_cache  # una sola conexión (con su pool) para todo el servicio
def obtener_redis() -> Redis:
    """Dependencia de FastAPI. decode_responses=True: Redis devuelve str en vez de bytes."""
    return Redis.from_url(obtener_configuracion().url_redis, decode_responses=True)
