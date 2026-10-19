from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from app.base_datos import Base


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
