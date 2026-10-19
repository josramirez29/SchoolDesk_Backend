from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from schooldesk_comun.errores import registrar_manejadores_errores
from schooldesk_comun.interno import requerir_clave_interna
from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import ALGORITMO_JWT, UsuarioActual, requerir_roles
from tests.conftest import CLAVE_INTERNA_PRUEBA, CLAVE_JWT_PRUEBA


def crear_token(rol: str = "ADMIN", clave: str = CLAVE_JWT_PRUEBA, minutos: int = 5) -> str:
    datos = {
        "sub": "100521347",
        "nombre": "Laura Méndez Ortega",
        "rol": rol,
        "exp": datetime.now(UTC) + timedelta(minutes=minutos),
    }
    return jwt.encode(datos, clave, algorithm=ALGORITMO_JWT)


def crear_cliente() -> TestClient:
    app = FastAPI()
    registrar_manejadores_errores(app)

    @app.get("/solo-admin")
    def solo_admin(usuario: UsuarioActual = Depends(requerir_roles(Rol.ADMIN))) -> dict[str, str]:
        return {"usuario": usuario.usuario, "rol": usuario.rol}

    @app.get("/interno/ping", dependencies=[Depends(requerir_clave_interna)])
    def ping_interno() -> dict[str, str]:
        return {"estado": "ok"}

    return TestClient(app)


def encabezado_auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_token_valido_con_rol_permitido_pasa() -> None:
    respuesta = crear_cliente().get("/solo-admin", headers=encabezado_auth(crear_token()))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"usuario": "100521347", "rol": "ADMIN"}


def test_sin_token_responde_401() -> None:
    respuesta = crear_cliente().get("/solo-admin")

    assert respuesta.status_code == 401
    assert respuesta.json()["error"] == "NO_AUTENTICADO"


def test_token_firmado_con_otra_clave_responde_401() -> None:
    token = crear_token(clave="otra-clave")

    respuesta = crear_cliente().get("/solo-admin", headers=encabezado_auth(token))

    assert respuesta.status_code == 401
    assert respuesta.json()["error"] == "TOKEN_INVALIDO"


def test_token_expirado_responde_401() -> None:
    token = crear_token(minutos=-1)

    respuesta = crear_cliente().get("/solo-admin", headers=encabezado_auth(token))

    assert respuesta.status_code == 401
    assert respuesta.json()["error"] == "TOKEN_EXPIRADO"


def test_rol_no_permitido_responde_403() -> None:
    token = crear_token(rol="ALUMNO")

    respuesta = crear_cliente().get("/solo-admin", headers=encabezado_auth(token))

    assert respuesta.status_code == 403
    assert respuesta.json()["error"] == "SIN_PERMISO"


def test_rol_desconocido_se_rechaza() -> None:
    # "Docente" no es un rol válido: solo existen los valores exactos del enum.
    token = crear_token(rol="Docente")

    respuesta = crear_cliente().get("/solo-admin", headers=encabezado_auth(token))

    assert respuesta.status_code == 401


def test_endpoint_interno_exige_clave() -> None:
    cliente = crear_cliente()

    assert cliente.get("/interno/ping").status_code == 401
    assert cliente.get("/interno/ping", headers={"X-Clave-Interna": "mala"}).status_code == 401
    correcta = cliente.get("/interno/ping", headers={"X-Clave-Interna": CLAVE_INTERNA_PRUEBA})
    assert correcta.status_code == 200
