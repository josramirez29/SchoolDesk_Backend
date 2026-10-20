"""Versiones falsas de los clientes de otros servicios.

Reemplazan al cliente real en las pruebas: no hacen llamadas HTTP, guardan lo
que se les pidió (para verificarlo) y se les puede indicar que fallen.
"""

from app.clientes.auth import ClienteAuth, CuentaAlumno, ResultadoLote
from schooldesk_comun.errores import ErrorApp


class ClienteAuthFalso(ClienteAuth):
    def __init__(self) -> None:  # no llama a super(): no necesita conexión HTTP
        self.cuentas_creadas: list[CuentaAlumno] = []
        self.nombres_actualizados: list[tuple[str, str, str]] = []
        self.error: ErrorApp | None = None  # si se asigna, cada llamada lo lanza

    def crear_cuentas_alumnos(self, cuentas: list[CuentaAlumno]) -> ResultadoLote:
        self._fallar_si_se_pidio()
        self.cuentas_creadas.extend(cuentas)
        return ResultadoLote(creados=[cuenta.usuario for cuenta in cuentas], omitidos=[])

    def actualizar_nombre(self, usuario: str, nombre: str, apellidos: str) -> None:
        self._fallar_si_se_pidio()
        self.nombres_actualizados.append((usuario, nombre, apellidos))

    def _fallar_si_se_pidio(self) -> None:
        if self.error is not None:
            raise self.error
