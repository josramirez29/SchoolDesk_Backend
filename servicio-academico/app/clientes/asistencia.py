"""Cliente HTTP para llamar a los endpoints /interno de servicio-asistencia."""

import httpx
from pydantic import BaseModel

from schooldesk_comun.cliente_interno import ClienteInterno


class AsistenciaDeAlumno(BaseModel):
    presentes: int
    retardos: int


class ResumenAsistencia(BaseModel):
    total_sesiones: int
    # Solo vienen los alumnos que asistieron al menos una vez; las faltas se
    # calculan aquí: total_sesiones - presentes - retardos.
    alumnos: dict[str, AsistenciaDeAlumno]


class ClienteAsistencia(ClienteInterno):
    def __init__(
        self,
        url_base: str,
        clave_interna: str,
        segundos_espera: float,
        transporte: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            url_base,
            clave_interna,
            segundos_espera,
            codigo_servicio="ASISTENCIA",
            nombre_servicio="El servicio de asistencia",
            transporte=transporte,
        )

    def obtener_resumen(self, nrc: str) -> ResumenAsistencia:
        respuesta = self._enviar("GET", f"/interno/materias/{nrc}/resumen")
        return ResumenAsistencia.model_validate(respuesta.json())
