"""Formato de los datos que entran y salen de la API (DTOs)."""

from pydantic import BaseModel, ConfigDict, Field

from schooldesk_comun.tipos import EmailNormalizado, Identificador

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
