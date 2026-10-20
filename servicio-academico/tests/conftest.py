from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from app import modelos  # noqa: F401  (registra las tablas en Base.metadata)
from app.base_datos import Base, obtener_sesion
from app.dependencias import obtener_cliente_asistencia, obtener_cliente_auth
from app.main import app
from schooldesk_comun.configuracion import obtener_configuracion_comun
from tests.falsos import ClienteAsistenciaFalso, ClienteAuthFalso

CLAVE_JWT_PRUEBA = "clave-jwt-de-prueba"
CLAVE_INTERNA_PRUEBA = "clave-interna-de-prueba"


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
def sesion(motor: Engine) -> Iterator[Session]:
    """Tablas nuevas y vacías para cada prueba, para que no se afecten entre sí."""
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as sesion:
        yield sesion
    Base.metadata.drop_all(motor)


@pytest.fixture
def auth_falso() -> ClienteAuthFalso:
    return ClienteAuthFalso()


@pytest.fixture
def asistencia_falso() -> ClienteAsistenciaFalso:
    return ClienteAsistenciaFalso()


@pytest.fixture
def cliente(
    sesion: Session, auth_falso: ClienteAuthFalso, asistencia_falso: ClienteAsistenciaFalso
) -> Iterator[TestClient]:
    """Cliente HTTP de la API con la base de pruebas y clientes falsos de los otros servicios."""
    app.dependency_overrides[obtener_sesion] = lambda: sesion
    app.dependency_overrides[obtener_cliente_auth] = lambda: auth_falso
    app.dependency_overrides[obtener_cliente_asistencia] = lambda: asistencia_falso
    yield TestClient(app)
    app.dependency_overrides.clear()
