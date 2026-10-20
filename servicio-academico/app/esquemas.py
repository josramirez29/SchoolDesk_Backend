"""Formato de los datos que entran y salen de la API (DTOs)."""

from pydantic import BaseModel, ConfigDict, Field

from schooldesk_comun.tipos import EmailNormalizado, Identificador, Nrc

# --- Alumnos ---


class AlumnoNuevo(BaseModel):
    matricula: Identificador
    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    # El email no se guarda en academic: se manda a auth, que es donde se usa.
    email: EmailNormalizado


class AlumnoEdicion(BaseModel):
    """Edición parcial del nombre. El email se edita en auth."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    apellidos: str | None = Field(default=None, min_length=1, max_length=100)


class AlumnoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    matricula: str
    nombre: str
    apellidos: str


class MateriaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nrc: str
    clave: str
    nombre: str
    seccion: str
    nombre_docente: str


class AlumnoDetalle(AlumnoRespuesta):
    materias: list[MateriaResumen]


# --- Materias e inscripciones ---

PATRON_SECCION = r"^\d{3}$"  # p. ej. "001"


class MateriaNueva(BaseModel):
    nrc: Nrc
    clave: str = Field(min_length=1, max_length=10, examples=["ITIS 702"])
    nombre: str = Field(min_length=1, max_length=100)
    seccion: str = Field(pattern=PATRON_SECCION, examples=["001"])
    num_empleado_docente: Identificador


class MateriaEdicion(BaseModel):
    """Edición parcial. El NRC no se edita: es el identificador que usan los demás servicios."""

    clave: str | None = Field(default=None, min_length=1, max_length=10)
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    seccion: str | None = Field(default=None, pattern=PATRON_SECCION)
    num_empleado_docente: Identificador | None = None


class MateriaRespuesta(MateriaResumen):
    num_empleado_docente: str


class InscripcionNueva(BaseModel):
    matricula: Identificador
