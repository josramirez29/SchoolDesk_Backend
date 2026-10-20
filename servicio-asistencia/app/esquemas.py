"""Formato de los datos que entran y salen de la API (DTOs)."""

from datetime import datetime

from pydantic import BaseModel, Field

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


# --- QR (alumno) y escaneo (docente) ---


class SolicitudQr(BaseModel):
    nrc: Nrc


class QrGenerado(BaseModel):
    """El frontend convierte `token` en la imagen del QR y pide otro antes de que expire."""

    token: str
    segundos_de_vida: int
    sesion_id: int


class Escaneo(BaseModel):
    token: str = Field(min_length=1, max_length=100)


class DatosQr(BaseModel):
    """Lo que se guarda en Redis junto al token. Nunca sale de este servicio."""

    sesion_id: int
    matricula: str
    nombre: str
