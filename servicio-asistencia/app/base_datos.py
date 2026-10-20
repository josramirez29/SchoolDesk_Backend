from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.configuracion import obtener_configuracion


class Base(DeclarativeBase):
    """Clase base de todos los modelos de este servicio."""


motor = create_engine(obtener_configuracion().url_base_datos)
FabricaSesiones = sessionmaker(bind=motor)


def obtener_bd() -> Iterator[Session]:
    """Dependencia de FastAPI: abre una conexión a la base por petición y siempre la cierra.

    En este servicio se llama `bd` (y no `sesion` como en los otros) para no
    confundirla con una sesión de asistencia (el modelo Sesion).
    """
    with FabricaSesiones() as bd:
        yield bd
