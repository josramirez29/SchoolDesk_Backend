from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from app.base_datos import Base, obtener_sesion
from app.configuracion import obtener_configuracion
from app.main import app
from app.modelos import Usuario
from schooldesk_comun.configuracion import obtener_configuracion_comun
from schooldesk_comun.roles import Rol
from tests.fabricas import nuevo_usuario

CLAVE_JWT_PRUEBA = "clave-jwt-de-prueba-con-al-menos-32-bytes"
CLAVE_INTERNA_PRUEBA = "clave-interna-de-prueba-de-32-bytes"


@pytest.fixture(autouse=True)
def entorno(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Claves de prueba para cada test (se aplica sola a todas las pruebas)."""
    monkeypatch.setenv("CLAVE_JWT", CLAVE_JWT_PRUEBA)
    monkeypatch.setenv("CLAVE_INTERNA", CLAVE_INTERNA_PRUEBA)
    # bcrypt con 4 rondas (el mínimo): las pruebas verifican que el hash funcione,
    # no su resistencia a ataques, y así no tardan minutos.
    monkeypatch.setenv("RONDAS_BCRYPT", "4")
    obtener_configuracion_comun.cache_clear()
    obtener_configuracion.cache_clear()
    yield
    obtener_configuracion_comun.cache_clear()
    obtener_configuracion.cache_clear()


@pytest.fixture(scope="session")
def motor() -> Iterator[Engine]:
    """PostgreSQL real dentro de un contenedor de Docker.

    Se levanta una sola vez para toda la corrida de pruebas (scope="session")
    porque arrancar el contenedor tarda unos segundos. Requiere Docker encendido.
    """
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
def cliente(sesion: Session) -> Iterator[TestClient]:
    """Cliente HTTP de la API que usa la base de pruebas en lugar de la real.

    dependency_overrides reemplaza la dependencia obtener_sesion: así se
    prueban las rutas completas sin tocar la configuración del servicio.
    """
    app.dependency_overrides[obtener_sesion] = lambda: sesion
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def admin(sesion: Session) -> Usuario:
    """Un admin ya guardado en la base, para las pruebas que lo necesitan."""
    admin = nuevo_usuario(
        usuario="100500001",
        nombre="Admin",
        apellidos="SchoolDesk",
        email="admin@example.com",
        rol=Rol.ADMIN,
    )
    sesion.add(admin)
    sesion.commit()
    return admin
