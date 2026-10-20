from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.configuracion import obtener_configuracion


class Base(DeclarativeBase):
    """Clase base de todos los modelos de este servicio."""


motor = create_engine(obtener_configuracion().url_base_datos)
FabricaSesiones = sessionmaker(bind=motor)


def obtener_sesion() -> Iterator[Session]:
    """Dependencia de FastAPI: abre una sesión por petición y siempre la cierra."""
    with FabricaSesiones() as sesion:
        yield sesion
