"""Formato de los datos que entran y salen de la API (DTOs).

Se separan del modelo de la base de datos para no exponer nunca campos
internos como `hash_contrasena`.
"""

from pydantic import BaseModel, ConfigDict, Field

from schooldesk_comun.roles import Rol
from schooldesk_comun.tipos import EmailNormalizado, Identificador


class SolicitudLogin(BaseModel):
    usuario: Identificador
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
    usuario: Identificador
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

    num_empleado: Identificador
    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    email: EmailNormalizado


COLUMNAS_DOCENTES = list(FilaDocente.model_fields)


# --- Endpoints internos (solo los llaman otros servicios) ---


class CuentaNueva(BaseModel):
    usuario: Identificador
    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    email: EmailNormalizado


class SolicitudLoteAlumnos(BaseModel):
    cuentas: list[CuentaNueva] = Field(min_length=1, max_length=2000)


class RespuestaLote(BaseModel):
    creados: list[str]
    omitidos: list[str]  # ya existían; se reportan para que la operación sea repetible


class DocenteResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario: str
    nombre: str
    apellidos: str
    email: str


class NombreActualizado(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
