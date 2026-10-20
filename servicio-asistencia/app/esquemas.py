"""Formato de los datos que entran y salen de la API (DTOs)."""

from datetime import datetime

from pydantic import BaseModel

from app.modelos import EstadoAsistencia
from schooldesk_comun.tipos import Nrc

# --- Sesiones (docente) ---


class SesionNueva(BaseModel):
    nrc: Nrc


class RegistroRespuesta(BaseModel):
    matricula: str
    nombre_alumno: str
    estado: EstadoAsistencia
    registrado_en: datetime


class SesionResumen(BaseModel):
    id: int
    nrc: str
    iniciada_en: datetime
    termina_en: datetime
    cerrada_en: datetime | None
    # Calculados con la hora actual (no se guardan en la base):
    activa: bool
    segundos_restantes: int
    presentes: int
    retardos: int


class SesionDetalle(SesionResumen):
    registros: list[RegistroRespuesta]  # en orden de llegada
