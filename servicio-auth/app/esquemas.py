"""Formato de los datos que entran y salen de la API (DTOs).

Se separan del modelo de la base de datos para no exponer nunca campos
internos como `hash_contrasena`.
"""

from pydantic import BaseModel, ConfigDict, Field

from schooldesk_comun.roles import Rol

PATRON_IDENTIFICADOR = r"^\d{9}$"  # matrícula o número de empleado BUAP


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
