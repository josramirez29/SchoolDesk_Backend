"""Modelos de la base de datos de servicio-academico.

    Alumno ──< Inscripcion >── Materia ──< Categoria ──< Tarea ──< Calificacion >── Alumno

Reglas sobre identificadores:
- Lo que cruza servicios usa identificadores estables: matrícula, NRC, número de empleado.
- Categorías y tareas usan un id autoincremental porque nunca salen de este servicio.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_datos import Base
from schooldesk_comun.tipos import COLACION_ESPANOL


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class Alumno(Base):
    """Registro académico del alumno. Su cuenta de acceso (y su email) viven en auth.

    El nombre se copia aquí a propósito para no consultar a auth en cada
    listado o reporte; se sincroniza al editarlo desde este servicio.
    """

    __tablename__ = "alumnos"

    matricula: Mapped[str] = mapped_column(String(9), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100, collation=COLACION_ESPANOL))
    apellidos: Mapped[str] = mapped_column(String(100, collation=COLACION_ESPANOL))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)

    inscripciones: Mapped[list["Inscripcion"]] = relationship(back_populates="alumno")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"


class Materia(Base):
    """Un grupo de una materia en el periodo, identificado por su NRC."""

    __tablename__ = "materias"

    nrc: Mapped[str] = mapped_column(String(5), primary_key=True)
    clave: Mapped[str] = mapped_column(String(10))  # p. ej. "ITIS 702"
    nombre: Mapped[str] = mapped_column(String(100, collation=COLACION_ESPANOL))
    seccion: Mapped[str] = mapped_column(String(3))  # p. ej. "001"
    # Docente titular. El nombre se copia al asignarlo, para que el alumno
    # vea quién le da clase sin tener permiso de consultar a auth.
    num_empleado_docente: Mapped[str] = mapped_column(String(9), index=True)
    nombre_docente: Mapped[str] = mapped_column(String(201))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)

    inscripciones: Mapped[list["Inscripcion"]] = relationship(back_populates="materia")
    categorias: Mapped[list["Categoria"]] = relationship(
        back_populates="materia", cascade="all, delete-orphan", order_by="Categoria.id"
    )


class Inscripcion(Base):
    """Un alumno inscrito en una materia. La llave compuesta impide inscribirlo dos veces."""

    __tablename__ = "inscripciones"

    nrc: Mapped[str] = mapped_column(ForeignKey("materias.nrc"), primary_key=True)
    matricula: Mapped[str] = mapped_column(ForeignKey("alumnos.matricula"), primary_key=True)
    inscrito_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)

    materia: Mapped[Materia] = relationship(back_populates="inscripciones")
    alumno: Mapped[Alumno] = relationship(back_populates="inscripciones")


class Categoria(Base):
    """Rubro de evaluación con su peso, p. ej. "Prácticas" 40 %.

    Que los pesos de una materia sumen 100 no se puede expresar como restricción
    de la base (involucra varias filas); lo valida el servicio al guardar la lista.
    """

    __tablename__ = "categorias"
    __table_args__ = (
        UniqueConstraint("nrc", "nombre"),
        CheckConstraint("peso > 0 AND peso <= 100", name="peso_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nrc: Mapped[str] = mapped_column(ForeignKey("materias.nrc"))
    nombre: Mapped[str] = mapped_column(String(50))
    # Decimal y no float: con float, 0.1 + 0.2 da 0.30000000000000004.
    peso: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    materia: Mapped[Materia] = relationship(back_populates="categorias")
    tareas: Mapped[list["Tarea"]] = relationship(
        back_populates="categoria", cascade="all, delete-orphan", order_by="Tarea.id"
    )


class Tarea(Base):
    """Actividad calificable dentro de una categoría, p. ej. "Práctica 3: Blog de café"."""

    __tablename__ = "tareas"
    __table_args__ = (UniqueConstraint("categoria_id", "nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"))
    nombre: Mapped[str] = mapped_column(String(100))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora_utc)

    categoria: Mapped[Categoria] = relationship(back_populates="tareas")
    calificaciones: Mapped[list["Calificacion"]] = relationship(back_populates="tarea")


class Calificacion(Base):
    """Puntos (0–100) de un alumno en una tarea.

    Si una tarea no está calificada, simplemente no hay fila: así "sin calificar"
    nunca se confunde con un 0.
    """

    __tablename__ = "calificaciones"
    __table_args__ = (CheckConstraint("puntos >= 0 AND puntos <= 100", name="puntos_validos"),)

    tarea_id: Mapped[int] = mapped_column(ForeignKey("tareas.id"), primary_key=True)
    matricula: Mapped[str] = mapped_column(ForeignKey("alumnos.matricula"), primary_key=True)
    puntos: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=ahora_utc, onupdate=ahora_utc
    )

    tarea: Mapped[Tarea] = relationship(back_populates="calificaciones")
