"""Pruebas del cliente HTTP real, con respuestas de auth simuladas (sin red)."""

from collections.abc import Callable

import httpx
import pytest

from app.clientes.auth import ClienteAuth, CuentaAlumno
from schooldesk_comun.errores import ErrorApp

CUENTA = CuentaAlumno(usuario="202231045", nombre="Ana", apellidos="Acosta", email="ana@example.com")


def cliente_con(responder: Callable[[httpx.Request], httpx.Response]) -> ClienteAuth:
    return ClienteAuth(
        url_base="http://auth",
        clave_interna="clave-secreta",
        segundos_espera=1,
        transporte=httpx.MockTransport(responder),
    )


def test_manda_la_clave_interna_y_lee_la_respuesta() -> None:
    peticiones: list[httpx.Request] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        peticiones.append(peticion)
        return httpx.Response(200, json={"creados": ["202231045"], "omitidos": []})

    resultado = cliente_con(responder).crear_cuentas_alumnos([CUENTA])

    assert resultado.creados == ["202231045"]
    assert peticiones[0].url.path == "/interno/usuarios/lote"
    assert peticiones[0].headers["X-Clave-Interna"] == "clave-secreta"


def test_error_de_negocio_se_reenvia_con_sus_datos() -> None:
    def responder(_: httpx.Request) -> httpx.Response:
        cuerpo = {"error": "EMAIL_EN_USO", "detalle": "Correo en uso", "emails": ["ana@example.com"]}
        return httpx.Response(409, json=cuerpo)

    with pytest.raises(ErrorApp) as error:
        cliente_con(responder).crear_cuentas_alumnos([CUENTA])

    assert error.value.codigo_http == 409
    assert error.value.error == "EMAIL_EN_USO"
    assert error.value.extra == {"emails": ["ana@example.com"]}


def test_auth_caido_se_convierte_en_503() -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=peticion)

    with pytest.raises(ErrorApp) as error:
        cliente_con(responder).crear_cuentas_alumnos([CUENTA])

    assert error.value.codigo_http == 503
    assert error.value.error == "AUTH_NO_DISPONIBLE"


def test_un_401_de_auth_no_se_reenvia_como_401() -> None:
    # Si la clave interna estuviera mal configurada, auth respondería 401.
    # Reenviarlo haría que el frontend cerrara la sesión del admin por error.
    def responder(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "CLAVE_INTERNA_INVALIDA", "detalle": "..."})

    with pytest.raises(ErrorApp) as error:
        cliente_con(responder).crear_cuentas_alumnos([CUENTA])

    assert error.value.codigo_http == 502
