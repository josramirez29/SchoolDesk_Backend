"""Formato de los datos que entran y salen de la API (DTOs).

Se separan del modelo de la base de datos para no exponer nunca campos
internos como `hash_contrasena`.
"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from schooldesk_comun.roles import Rol

PATRON_IDENTIFICADOR = r"^\d{9}$"  # matrícula o número de empleado BUAP


# "Laura.Mendez@..." y "laura.mendez@..." son el mismo correo: se guarda en minúsculas.
EmailNormalizado = Annotated[EmailStr, AfterValidator(str.lower)]


class SolicitudLogin(BaseModel):
    usuario: str = Field(pattern=PATRON_IDENTIFICADOR, examples=["100521347"])
    contrasena: str = Field(min_length=1, max_length=72)  # bcrypt solo usa 72 bytes


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # permite crearlo desde el modelo

    usuario: str
    nombre: str
    apellidos: str
    email: str
    rol: Rol
    activo: bool


class RespuestaLogin(BaseModel):
    token_acceso: str
    tipo_token: str = "bearer"
    usuario: UsuarioRespuesta


class UsuarioNuevo(BaseModel):
    usuario: str = Field(pattern=PATRON_IDENTIFICADOR, examples=["100521347"])
    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    email: EmailNormalizado
    rol: Rol


class UsuarioEdicion(BaseModel):
    """Edición parcial: solo se cambian los campos que vengan en la petición."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    apellidos: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailNormalizado | None = None
    activo: bool | None = None
    restablecer_contrasena: bool = False


class CambioContrasena(BaseModel):
    contrasena_actual: str = Field(min_length=1, max_length=72)
    contrasena_nueva: str = Field(min_length=8, max_length=72)


class FilaDocente(BaseModel):
    """Una fila de docentes.csv. Los nombres de los campos son las columnas del archivo."""

    num_empleado: str = Field(pattern=PATRON_IDENTIFICADOR)
    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    email: EmailNormalizado


COLUMNAS_DOCENTES = list(FilaDocente.model_fields)
