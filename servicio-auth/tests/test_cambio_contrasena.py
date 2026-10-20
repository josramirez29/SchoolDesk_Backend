import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos import Usuario
from tests.fabricas import CONTRASENA_PRUEBA, encabezado_de, nuevo_usuario


@pytest.fixture
def docente(sesion: Session) -> Usuario:
    docente = nuevo_usuario()
    sesion.add(docente)
    sesion.commit()
    return docente


def cambiar(cliente: TestClient, docente: Usuario, actual: str, nueva: str) -> int:
    respuesta = cliente.put(
        "/perfil/contrasena",
        json={"contrasena_actual": actual, "contrasena_nueva": nueva},
        headers=encabezado_de(docente),
    )
    return respuesta.status_code


def test_cambio_correcto_permite_entrar_con_la_nueva(cliente: TestClient, docente: Usuario) -> None:
    assert cambiar(cliente, docente, CONTRASENA_PRUEBA, "nueva-contrasena-456") == 204

    vieja = cliente.post(
        "/login", json={"usuario": docente.usuario, "contrasena": CONTRASENA_PRUEBA}
    )
    nueva = cliente.post(
        "/login", json={"usuario": docente.usuario, "contrasena": "nueva-contrasena-456"}
    )
    assert vieja.status_code == 401
    assert nueva.status_code == 200


def test_contrasena_actual_incorrecta_responde_422_y_no_401(
    cliente: TestClient, docente: Usuario
) -> None:
    assert cambiar(cliente, docente, "no-es-la-actual", "nueva-contrasena-456") == 422


def test_no_se_permite_usar_el_numero_de_empleado(cliente: TestClient, docente: Usuario) -> None:
    assert cambiar(cliente, docente, CONTRASENA_PRUEBA, docente.usuario) == 422


def test_contrasena_nueva_de_menos_de_8_caracteres_se_rechaza(
    cliente: TestClient, docente: Usuario
) -> None:
    assert cambiar(cliente, docente, CONTRASENA_PRUEBA, "corta") == 422
