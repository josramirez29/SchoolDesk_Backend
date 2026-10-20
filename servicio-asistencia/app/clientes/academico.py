"""Cliente HTTP para llamar a los endpoints /interno de servicio-academico.

La clave interna, el tiempo de espera y la traducción de errores vienen de
ClienteInterno (comun). En las pruebas se reemplaza por un cliente falso.
"""

import httpx
from pydantic import BaseModel

from schooldesk_comun.cliente_interno import ClienteInterno


class MateriaAcademica(BaseModel):
    nrc: str
    nombre: str
    num_empleado_docente: str


class AlumnoInscrito(BaseModel):
    matricula: str
    nombre: str
    apellidos: str

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"


class ClienteAcademico(ClienteInterno):
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
            codigo_servicio="ACADEMICO",
            nombre_servicio="El servicio académico",
            transporte=transporte,
        )

    def obtener_materia(self, nrc: str) -> MateriaAcademica:
        """Para verificar que quien abre la sesión es el docente titular."""
        respuesta = self._enviar("GET", f"/interno/materias/{nrc}")
        return MateriaAcademica.model_validate(respuesta.json())

    def obtener_alumno_inscrito(self, nrc: str, matricula: str) -> AlumnoInscrito:
        """El alumno, si está inscrito. Si no, academic responde 404 NO_INSCRITO."""
        respuesta = self._enviar("GET", f"/interno/materias/{nrc}/alumnos/{matricula}")
        return AlumnoInscrito.model_validate(respuesta.json())
