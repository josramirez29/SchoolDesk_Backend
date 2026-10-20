"""Base para que un servicio llame a los endpoints /interno de otro.

Concentra en un solo lugar lo que toda llamada entre servicios necesita:
la clave interna, un tiempo máximo de espera y cómo traducir los errores.
"""

import httpx

from schooldesk_comun.errores import ErrorApp

# Errores del otro servicio que son de negocio y tienen sentido para quien hizo la
# petición (p. ej. "ese correo ya existe"). Cualquier otro (401, 500...) es un
# problema entre servicios y no se reenvía tal cual: un 401 haría que el frontend
# cerrara la sesión del usuario, aunque su token esté bien.
CODIGOS_QUE_SE_REENVIAN = {404, 409, 422}


class ClienteInterno:
    def __init__(
        self,
        url_base: str,
        clave_interna: str,
        segundos_espera: float,
        codigo_servicio: str,  # p. ej. "AUTH" → errores AUTH_NO_DISPONIBLE, ERROR_EN_AUTH
        nombre_servicio: str,  # p. ej. "El servicio de cuentas", para los mensajes
        transporte: httpx.BaseTransport | None = None,  # las pruebas inyectan uno falso
    ) -> None:
        self._codigo_servicio = codigo_servicio
        self._nombre_servicio = nombre_servicio
        self._http = httpx.Client(
            base_url=url_base,
            headers={"X-Clave-Interna": clave_interna},
            timeout=segundos_espera,
            transport=transporte,
        )

    def _enviar(self, metodo: str, ruta: str, **opciones: object) -> httpx.Response:
        try:
            respuesta = self._http.request(metodo, ruta, **opciones)
        except httpx.HTTPError:
            # Timeout o servicio caído: quien llama debe saber que puede reintentar.
            raise ErrorApp(
                503,
                f"{self._codigo_servicio}_NO_DISPONIBLE",
                f"{self._nombre_servicio} no responde, intenta de nuevo en unos minutos",
            )

        if respuesta.is_success:
            return respuesta
        if respuesta.status_code in CODIGOS_QUE_SE_REENVIAN:
            cuerpo = respuesta.json()
            extra = {
                campo: valor for campo, valor in cuerpo.items() if campo not in ("error", "detalle")
            }
            raise ErrorApp(respuesta.status_code, cuerpo["error"], cuerpo["detalle"], extra)
        raise ErrorApp(
            502,
            f"ERROR_EN_{self._codigo_servicio}",
            f"{self._nombre_servicio} respondió con un error inesperado",
        )
