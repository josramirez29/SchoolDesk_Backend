from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.modelos import Usuario
from schooldesk_comun.roles import Rol
from tests.conftest import CLAVE_INTERNA_PRUEBA
from tests.fabricas import nuevo_usuario

CLAVE = {"X-Clave-Interna": CLAVE_INTERNA_PRUEBA}

ANA = {
    "usuario": "202231045",
    "nombre": "Ana Sofía",
    "apellidos": "Acosta Bravo",
    "email": "ana.acosta@alumno.example.com",
}
BRUNO = {
    "usuario": "202233918",
    "nombre": "Bruno",
    "apellidos": "Aguilar Campos",
    "email": "bruno.aguilar@alumno.example.com",
}


def crear_lote(cliente: TestClient, *cuentas: dict[str, str]) -> Response:
    return cliente.post("/interno/usuarios/lote", json={"cuentas": list(cuentas)}, headers=CLAVE)


def test_sin_clave_interna_responde_401(cliente: TestClient) -> None:
    respuesta = cliente.post("/interno/usuarios/lote", json={"cuentas": [ANA]})

    assert respuesta.status_code == 401
    assert respuesta.json()["error"] == "CLAVE_INTERNA_INVALIDA"


def test_crea_cuentas_de_alumno_que_entran_con_su_matricula(
    cliente: TestClient, sesion: Session
) -> None:
    respuesta = crear_lote(cliente, ANA, BRUNO)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"creados": ["202231045", "202233918"], "omitidos": []}
    assert sesion.get(Usuario, "202231045").rol == Rol.ALUMNO
    login = cliente.post("/login", json={"usuario": "202231045", "contrasena": "202231045"})
    assert login.status_code == 200


def test_repetir_el_lote_omite_las_que_ya_existen(cliente: TestClient) -> None:
    crear_lote(cliente, ANA)

    respuesta = crear_lote(cliente, ANA, BRUNO)

    assert respuesta.json() == {"creados": ["202233918"], "omitidos": ["202231045"]}


def test_email_de_otra_cuenta_no_crea_nada(cliente: TestClient, sesion: Session) -> None:
    sesion.add(nuevo_usuario(email="bruno.aguilar@alumno.example.com"))  # un docente
    sesion.commit()

    respuesta = crear_lote(cliente, ANA, BRUNO)

    assert respuesta.status_code == 409
    assert respuesta.json()["emails"] == ["bruno.aguilar@alumno.example.com"]
    assert sesion.get(Usuario, "202231045") is None  # Ana tampoco se creó


def test_matricula_que_es_de_un_docente_se_rechaza(cliente: TestClient, sesion: Session) -> None:
    sesion.add(nuevo_usuario(usuario="202231045"))  # docente con ese número
    sesion.commit()

    respuesta = crear_lote(cliente, ANA)

    assert respuesta.status_code == 409
    assert respuesta.json()["usuarios"] == ["202231045"]


def test_lote_con_matricula_repetida_responde_422(cliente: TestClient) -> None:
    respuesta = crear_lote(cliente, ANA, {**ANA, "email": "otra@alumno.example.com"})

    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "LOTE_CON_REPETIDOS"


def test_lista_solo_docentes_activos(cliente: TestClient, sesion: Session, admin: Usuario) -> None:
    sesion.add_all(
        [
            nuevo_usuario(),  # docente activo
            nuevo_usuario(usuario="100534812", email="r@docente.example.com", activo=False),
        ]
    )
    sesion.commit()

    respuesta = cliente.get("/interno/docentes", headers=CLAVE)

    assert respuesta.status_code == 200
    assert [d["usuario"] for d in respuesta.json()] == ["100521347"]  # ni el inactivo ni el admin


def test_actualizar_nombre_cambia_el_nombre_del_token(cliente: TestClient) -> None:
    crear_lote(cliente, ANA)

    respuesta = cliente.patch(
        "/interno/usuarios/202231045/nombre",
        json={"nombre": "Ana Sofía", "apellidos": "Acosta Bravo de la Cruz"},
        headers=CLAVE,
    )

    assert respuesta.status_code == 204
    login = cliente.post("/login", json={"usuario": "202231045", "contrasena": "202231045"})
    assert login.json()["usuario"]["apellidos"] == "Acosta Bravo de la Cruz"


def test_actualizar_nombre_de_usuario_inexistente_responde_404(cliente: TestClient) -> None:
    respuesta = cliente.patch(
        "/interno/usuarios/202299999/nombre",
        json={"nombre": "Nadie", "apellidos": "Nadie"},
        headers=CLAVE,
    )

    assert respuesta.status_code == 404
