from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from redis import Redis
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app import modelos  # noqa: F401  (registra las tablas en Base.metadata)
from app.base_datos import Base, obtener_bd
from app.dependencias import obtener_cliente_academico
from app.main import app
from app.redis_cliente import obtener_redis
from app.reloj import obtener_ahora
from schooldesk_comun.configuracion import obtener_configuracion_comun
from tests.claves import CLAVE_INTERNA_PRUEBA, CLAVE_JWT_PRUEBA
from tests.falsos import ClienteAcademicoFalso, RelojFalso


@pytest.fixture(autouse=True)
def entorno(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Claves de prueba para cada test (se aplica sola a todas las pruebas)."""
    monkeypatch.setenv("CLAVE_JWT", CLAVE_JWT_PRUEBA)
    monkeypatch.setenv("CLAVE_INTERNA", CLAVE_INTERNA_PRUEBA)
    obtener_configuracion_comun.cache_clear()
    yield
    obtener_configuracion_comun.cache_clear()


@pytest.fixture(scope="session")
def motor() -> Iterator[Engine]:
    """PostgreSQL real dentro de un contenedor de Docker, uno para toda la corrida."""
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        motor = create_engine(postgres.get_connection_url())
        yield motor
        motor.dispose()


@pytest.fixture
def bd(motor: Engine) -> Iterator[Session]:
    """Tablas nuevas y vacías para cada prueba, para que no se afecten entre sí."""
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as bd:
        yield bd
    Base.metadata.drop_all(motor)


@pytest.fixture(scope="session")
def contenedor_redis() -> Iterator[RedisContainer]:
    """Redis real dentro de un contenedor de Docker, uno para toda la corrida."""
    with RedisContainer("redis:7-alpine") as contenedor:
        yield contenedor


@pytest.fixture
def redis(contenedor_redis: RedisContainer) -> Iterator[Redis]:
    """Redis vacío para cada prueba."""
    cliente = contenedor_redis.get_client(decode_responses=True)
    cliente.flushdb()
    yield cliente
    cliente.close()


@pytest.fixture
def academico_falso() -> ClienteAcademicoFalso:
    return ClienteAcademicoFalso()


@pytest.fixture
def reloj() -> RelojFalso:
    return RelojFalso()


@pytest.fixture
def cliente(
    bd: Session, redis: Redis, academico_falso: ClienteAcademicoFalso, reloj: RelojFalso
) -> Iterator[TestClient]:
    """Cliente HTTP de la API con la base y Redis de prueba, academic falso y reloj falso."""
    app.dependency_overrides[obtener_bd] = lambda: bd
    app.dependency_overrides[obtener_redis] = lambda: redis
    app.dependency_overrides[obtener_cliente_academico] = lambda: academico_falso
    app.dependency_overrides[obtener_ahora] = lambda: reloj.ahora
    yield TestClient(app)
    app.dependency_overrides.clear()

