from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.base_datos import Base
from schooldesk_comun.roles import Rol


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class Usuario(Base):
    """Cuenta para iniciar sesión en SchoolDesk.

    La llave primaria es `usuario`: la matrícula (alumno) o el número de
    empleado (docente/admin). No hay un id autoincremental porque ese id
    solo tendría sentido dentro de esta base, y los demás servicios
    necesitan un identificador que sea el mismo en todas partes.
    """

    __tablename__ = "usuarios"

    usuario: Mapped[str] = mapped_column(String(9), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    apellidos: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    hash_contrasena: Mapped[str] = mapped_column(String(60))  # bcrypt siempre mide 60
    rol: Mapped[Rol] = mapped_column(Enum(Rol, native_enum=False, length=10))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=ahora_utc, onupdate=ahora_utc
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"
