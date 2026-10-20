"""Cliente HTTP para llamar a los endpoints /interno de servicio-auth.

Todo lo que academic necesita de auth pasa por esta clase. Así, en las pruebas
se reemplaza por un cliente falso y no hace falta levantar servicio-auth.
La clave interna, el tiempo de espera y la traducción de errores vienen de
ClienteInterno (comun).
"""

import httpx
from pydantic import BaseModel

from schooldesk_comun.cliente_interno import ClienteInterno


class CuentaAlumno(BaseModel):
    usuario: str
    nombre: str
    apellidos: str
    email: str


class ResultadoLote(BaseModel):
    creados: list[str]
    omitidos: list[str]


class Docente(BaseModel):
    usuario: str
    nombre: str
    apellidos: str

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"


class ClienteAuth(ClienteInterno):
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
            codigo_servicio="AUTH",
            nombre_servicio="El servicio de cuentas",
            transporte=transporte,
        )

    def crear_cuentas_alumnos(self, cuentas: list[CuentaAlumno]) -> ResultadoLote:
        cuerpo = {"cuentas": [cuenta.model_dump() for cuenta in cuentas]}
        respuesta = self._enviar("POST", "/interno/usuarios/lote", json=cuerpo)
        return ResultadoLote.model_validate(respuesta.json())

    def actualizar_nombre(self, usuario: str, nombre: str, apellidos: str) -> None:
        cuerpo = {"nombre": nombre, "apellidos": apellidos}
        self._enviar("PATCH", f"/interno/usuarios/{usuario}/nombre", json=cuerpo)

    def listar_docentes(self) -> list[Docente]:
        """Docentes activos. Se usa para validar al docente titular de una materia."""
        respuesta = self._enviar("GET", "/interno/docentes")
        return [Docente.model_validate(docente) for docente in respuesta.json()]
