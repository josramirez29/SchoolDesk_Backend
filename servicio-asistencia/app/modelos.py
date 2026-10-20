"""Modelos de la base de datos de servicio-asistencia.

    Sesion ──< Registro

Aquí solo vive lo que debe guardarse (el historial). Los tokens de QR, que
duran 30 segundos y se usan una vez, viven en Redis.
"""

from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_datos import Base


class EstadoAsistencia(StrEnum):
    PRESENTE = "PRESENTE"
    RETARDO = "RETARDO"
    # No hay FALTA: una falta es que no exista registro (igual que "sin calificar").


class Sesion(Base):
    """Sesión de asistencia de una materia, abierta por su docente.

    Que solo haya una sesión activa por materia no se puede expresar como
    restricción de la base (depende de la hora actual); lo valida el servicio.
    """

    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    nrc: Mapped[str] = mapped_column(String(5), index=True)
    num_empleado_docente: Mapped[str] = mapped_column(String(9))
    iniciada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    termina_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    registros: Mapped[list["Registro"]] = relationship(
        back_populates="sesion", cascade="all, delete-orphan", order_by="Registro.registrado_en"
    )

    def esta_activa(self, ahora: datetime) -> bool:
        return self.cerrada_en is None and ahora < self.termina_en

    def segundos_restantes(self, ahora: datetime) -> int:
        if not self.esta_activa(ahora):
            return 0
        return int((self.termina_en - ahora).total_seconds())

    def estado_para(self, ahora: datetime, minutos_tolerancia: int) -> EstadoAsistencia:
        """PRESENTE si se registra dentro de la tolerancia (inclusive); si no, RETARDO."""
        if ahora - self.iniciada_en <= timedelta(minutes=minutos_tolerancia):
            return EstadoAsistencia.PRESENTE
        return EstadoAsistencia.RETARDO


class Registro(Base):
    """Asistencia de un alumno en una sesión. La llave compuesta impide registrarlo dos veces."""

    __tablename__ = "registros"

    sesion_id: Mapped[int] = mapped_column(ForeignKey("sesiones.id"), primary_key=True)
    matricula: Mapped[str] = mapped_column(String(9), primary_key=True)
    # Copia del nombre (viene de academic al generar el QR) para mostrar la lista
    # de la sesión sin consultar a academic por cada alumno.
    nombre_alumno: Mapped[str] = mapped_column(String(201))
    estado: Mapped[EstadoAsistencia] = mapped_column(
        Enum(EstadoAsistencia, native_enum=False, length=10)
    )
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    sesion: Mapped[Sesion] = relationship(back_populates="registros")
