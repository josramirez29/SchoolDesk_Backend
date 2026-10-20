"""Cliente HTTP para llamar a los endpoints /interno de servicio-auth.

Todo lo que academic necesita de auth pasa por esta clase. Así, en las pruebas
se reemplaza por un cliente falso y no hace falta levantar servicio-auth.
"""

import httpx
from pydantic import BaseModel

from schooldesk_comun.errores import ErrorApp

# Errores de auth que son de negocio y tienen sentido para quien hizo la petición
# (p. ej. "ese correo ya existe"). Cualquier otro (401, 500...) es un problema
# entre servicios y no se reenvía tal cual: un 401 haría que el frontend cerrara
# la sesión del admin, aunque su token esté bien.
CODIGOS_QUE_SE_REENVIAN = {404, 409, 422}


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


class ClienteAuth:
    def __init__(
        self,
        url_base: str,
        clave_interna: str,
        segundos_espera: float,
        transporte: httpx.BaseTransport | None = None,  # las pruebas inyectan uno falso
    ) -> None:
        self._http = httpx.Client(
            base_url=url_base,
            headers={"X-Clave-Interna": clave_interna},
            timeout=segundos_espera,
            transport=transporte,
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

    def _enviar(self, metodo: str, ruta: str, **opciones: object) -> httpx.Response:
        try:
            respuesta = self._http.request(metodo, ruta, **opciones)
        except httpx.HTTPError:
            # Timeout o servicio caído: el cliente debe saber que puede reintentar.
            raise ErrorApp(
                503,
                "AUTH_NO_DISPONIBLE",
                "El servicio de cuentas no responde, intenta de nuevo en unos minutos",
            )

        if respuesta.is_success:
            return respuesta
        if respuesta.status_code in CODIGOS_QUE_SE_REENVIAN:
            cuerpo = respuesta.json()
            extra = {campo: valor for campo, valor in cuerpo.items() if campo not in ("error", "detalle")}
            raise ErrorApp(respuesta.status_code, cuerpo["error"], cuerpo["detalle"], extra)
        raise ErrorApp(502, "ERROR_EN_AUTH", "El servicio de cuentas respondió con un error inesperado")
