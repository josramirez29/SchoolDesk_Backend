from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import decodificar_token
from tests.conftest import CLAVE_JWT_PRUEBA
from tests.fabricas import CONTRASENA_PRUEBA, nuevo_usuario


def hacer_login(cliente: TestClient, usuario: str, contrasena: str) -> Response:
    return cliente.post("/login", json={"usuario": usuario, "contrasena": contrasena})


def test_login_correcto_devuelve_token_con_identidad_y_rol(cliente: TestClient, sesion: Session) -> None:
    sesion.add(nuevo_usuario())
    sesion.commit()

    respuesta = hacer_login(cliente, "100521347", CONTRASENA_PRUEBA)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["usuario"] == "100521347"
    assert "hash_contrasena" not in cuerpo["usuario"]
    # El token lo puede validar cualquier servicio con la clave compartida.
    actual = decodificar_token(cuerpo["token_acceso"], CLAVE_JWT_PRUEBA)
    assert actual.usuario == "100521347"
    assert actual.nombre == "Laura Méndez Ortega"
    assert actual.rol == Rol.DOCENTE


def test_contrasena_incorrecta_responde_401(cliente: TestClient, sesion: Session) -> None:
    sesion.add(nuevo_usuario())
    sesion.commit()

    respuesta = hacer_login(cliente, "100521347", "incorrecta")

    assert respuesta.status_code == 401
    assert respuesta.json()["error"] == "CREDENCIALES_INVALIDAS"


def test_usuario_inexistente_responde_igual_que_contrasena_incorrecta(cliente: TestClient) -> None:
    respuesta = hacer_login(cliente, "999999999", "cualquiera")

    assert respuesta.status_code == 401
    assert respuesta.json() == {
        "error": "CREDENCIALES_INVALIDAS",
        "detalle": "Usuario o contraseña incorrectos",
    }


def test_cuenta_desactivada_no_puede_entrar(cliente: TestClient, sesion: Session) -> None:
    sesion.add(nuevo_usuario(activo=False))
    sesion.commit()

    respuesta = hacer_login(cliente, "100521347", CONTRASENA_PRUEBA)

    assert respuesta.status_code == 403
    assert respuesta.json()["error"] == "CUENTA_DESACTIVADA"


def test_usuario_con_formato_invalido_responde_422(cliente: TestClient) -> None:
    respuesta = hacer_login(cliente, "abc", "cualquiera")

    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "VALIDACION"


def test_perfil_devuelve_al_usuario_del_token(cliente: TestClient, sesion: Session) -> None:
    sesion.add(nuevo_usuario())
    sesion.commit()
    token = hacer_login(cliente, "100521347", CONTRASENA_PRUEBA).json()["token_acceso"]

    respuesta = cliente.get("/perfil", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == "laura.mendez@docente.example.com"


def test_perfil_sin_token_responde_401(cliente: TestClient) -> None:
    respuesta = cliente.get("/perfil")

    assert respuesta.status_code == 401
