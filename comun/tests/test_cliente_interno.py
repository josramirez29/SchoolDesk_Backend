"""Pruebas del cliente base, con respuestas simuladas (sin red)."""

from collections.abc import Callable

import httpx
import pytest

from schooldesk_comun.cliente_interno import ClienteInterno
from schooldesk_comun.errores import ErrorApp


def cliente_con(responder: Callable[[httpx.Request], httpx.Response]) -> ClienteInterno:
    return ClienteInterno(
        url_base="http://otro-servicio",
        clave_interna="clave-secreta",
        segundos_espera=1,
        codigo_servicio="PRUEBA",
        nombre_servicio="El servicio de prueba",
        transporte=httpx.MockTransport(responder),
    )


def test_manda_la_clave_interna() -> None:
    recibidas: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        recibidas.append(peticion)
        return httpx.Response(200, json={})

    cliente_con(responder)._enviar("GET", "/interno/algo")

    assert recibidas[0].headers["X-Clave-Interna"] == "clave-secreta"


def test_servicio_caido_se_convierte_en_503() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=peticion)

    with pytest.raises(ErrorApp) as error:
        cliente_con(responder)._enviar("GET", "/interno/algo")

    assert (error.value.codigo_http, error.value.error) == (503, "PRUEBA_NO_DISPONIBLE")


def test_error_de_negocio_se_reenvia_con_sus_datos() -> None:
    def responder(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "DUPLICADO", "detalle": "Ya existe", "ids": [1]})

    with pytest.raises(ErrorApp) as error:
        cliente_con(responder)._enviar("GET", "/interno/algo")

    assert (error.value.codigo_http, error.value.error, error.value.extra) == (409, "DUPLICADO", {"ids": [1]})


@pytest.mark.parametrize("codigo", [401, 500])
def test_otros_errores_se_convierten_en_502(codigo: int) -> None:
    def responder(_: httpx.Request) -> httpx.Response:
        return httpx.Response(codigo, json={"error": "X", "detalle": "X"})

    with pytest.raises(ErrorApp) as error:
        cliente_con(responder)._enviar("GET", "/interno/algo")

    assert (error.value.codigo_http, error.value.error) == (502, "ERROR_EN_PRUEBA")
