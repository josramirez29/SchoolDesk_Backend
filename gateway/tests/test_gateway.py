"""Pruebas del gateway con los 3 servicios simulados (httpx.MockTransport, sin red)."""

from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, obtener_cliente_http

Responder = Callable[[httpx.Request], httpx.Response]


class ServiciosSimulados:
    """Guarda las peticiones que llegan a los servicios y decide qué responden."""

    def __init__(self) -> None:
        self.recibidas: list[httpx.Request] = []
        self.responder: Responder = lambda _: httpx.Response(200, json={"ok": True})

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.recibidas.append(peticion)
        return self.responder(peticion)


@pytest.fixture
def servicios() -> ServiciosSimulados:
    return ServiciosSimulados()


@pytest.fixture
def cliente(servicios: ServiciosSimulados) -> Iterator[TestClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(servicios))
    app.dependency_overrides[obtener_cliente_http] = lambda: http
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- Enrutamiento ---


@pytest.mark.parametrize(
    ("ruta", "destino"),
    [
        ("/api/auth/login", "http://localhost:8001/login"),
        ("/api/academico/materias/48308", "http://localhost:8002/materias/48308"),
        ("/api/asistencia/sesiones/7/escanear", "http://localhost:8003/sesiones/7/escanear"),
    ],
)
def test_cada_prefijo_llega_a_su_servicio(
    cliente: TestClient, servicios: ServiciosSimulados, ruta: str, destino: str
) -> None:
    cliente.post(ruta, json={})

    assert str(servicios.recibidas[0].url) == destino


def test_reenvia_metodo_cuerpo_token_y_parametros(
    cliente: TestClient, servicios: ServiciosSimulados
) -> None:
    cliente.patch(
        "/api/academico/alumnos/202231045",
        params={"buscar": "ana", "extra": "1"},
        json={"nombre": "Ana"},
        headers={"Authorization": "Bearer abc"},
    )

    recibida = servicios.recibidas[0]
    assert recibida.method == "PATCH"
    assert recibida.url.params["buscar"] == "ana"
    assert recibida.headers["Authorization"] == "Bearer abc"
    assert recibida.content == b'{"nombre":"Ana"}'


def test_devuelve_la_respuesta_del_servicio_tal_cual(
    cliente: TestClient, servicios: ServiciosSimulados
) -> None:
    servicios.responder = lambda _: httpx.Response(
        409, json={"error": "YA_INSCRITO", "detalle": "Ya está inscrito"}
    )

    respuesta = cliente.post("/api/academico/materias/48308/alumnos", json={})

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "YA_INSCRITO"


def test_servicio_desconocido_responde_404(cliente: TestClient, servicios: ServiciosSimulados) -> None:
    respuesta = cliente.get("/api/calificaciones/algo")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "SERVICIO_DESCONOCIDO"
    assert servicios.recibidas == []


# --- Seguridad ---


@pytest.mark.parametrize(
    "ruta", ["/api/auth/interno/docentes", "/api/academico/interno", "/api/asistencia/interno/x/y"]
)
def test_las_rutas_internas_no_existen_desde_fuera(
    cliente: TestClient, servicios: ServiciosSimulados, ruta: str
) -> None:
    respuesta = cliente.get(ruta, headers={"X-Clave-Interna": "intento"})

    assert respuesta.status_code == 404
    assert servicios.recibidas == []  # ni siquiera llegó al servicio


def test_no_reenvia_una_clave_interna_enviada_desde_fuera(
    cliente: TestClient, servicios: ServiciosSimulados
) -> None:
    cliente.get("/api/academico/materias", headers={"X-Clave-Interna": "intento"})

    assert "x-clave-interna" not in servicios.recibidas[0].headers


def test_una_ruta_que_solo_empieza_parecido_no_se_bloquea(
    cliente: TestClient, servicios: ServiciosSimulados
) -> None:
    cliente.get("/api/academico/internos")  # no es /interno

    assert len(servicios.recibidas) == 1


# --- Servicios caídos ---


def test_servicio_caido_responde_503_con_el_formato_comun(
    cliente: TestClient, servicios: ServiciosSimulados
) -> None:
    def caido(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=peticion)

    servicios.responder = caido

    respuesta = cliente.get("/api/asistencia/sesiones?nrc=48308")

    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "error": "SERVICIO_NO_DISPONIBLE",
        "detalle": "El servicio asistencia no está disponible",
    }


def test_servicio_lento_responde_504(cliente: TestClient, servicios: ServiciosSimulados) -> None:
    def lento(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sin respuesta", request=peticion)

    servicios.responder = lento

    assert cliente.get("/api/academico/materias").status_code == 504


def test_salud_de_los_servicios(cliente: TestClient, servicios: ServiciosSimulados) -> None:
    def responder(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.port == 8003:  # asistencia
            raise httpx.ConnectError("caído", request=peticion)
        return httpx.Response(200, json={"estado": "ok"})

    servicios.responder = responder

    respuesta = cliente.get("/salud/servicios")

    assert respuesta.json() == {"auth": "ok", "academico": "ok", "asistencia": "caido"}


# --- CORS ---


def test_cors_permite_al_frontend(cliente: TestClient) -> None:
    respuesta = cliente.options(
        "/api/auth/login",
        headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "POST"},
    )

    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:4200"


def test_cors_no_permite_otros_origenes(cliente: TestClient) -> None:
    respuesta = cliente.options(
        "/api/auth/login",
        headers={"Origin": "https://sitio-malicioso.example", "Access-Control-Request-Method": "POST"},
    )

    assert "access-control-allow-origin" not in respuesta.headers
