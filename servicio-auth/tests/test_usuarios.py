from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos import Usuario
from tests.fabricas import CONTRASENA_PRUEBA, encabezado_de, nuevo_usuario

DOCENTE_NUEVO = {
    "usuario": "100534812",
    "nombre": "Ricardo",
    "apellidos": "Salinas Pérez",
    "email": "ricardo.salinas@docente.example.com",
    "rol": "DOCENTE",
}


def test_admin_crea_docente_que_entra_con_su_numero_de_empleado(
    cliente: TestClient, admin: Usuario
) -> None:
    respuesta = cliente.post("/usuarios", json=DOCENTE_NUEVO, headers=encabezado_de(admin))

    assert respuesta.status_code == 201
    assert respuesta.json()["activo"] is True
    login = cliente.post("/login", json={"usuario": "100534812", "contrasena": "100534812"})
    assert login.status_code == 200


def test_no_se_crean_cuentas_de_alumno_desde_aqui(cliente: TestClient, admin: Usuario) -> None:
    alumno = {**DOCENTE_NUEVO, "usuario": "202231045", "rol": "ALUMNO"}

    respuesta = cliente.post("/usuarios", json=alumno, headers=encabezado_de(admin))

    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "ROL_NO_PERMITIDO"


def test_usuario_repetido_responde_409(cliente: TestClient, admin: Usuario) -> None:
    cliente.post("/usuarios", json=DOCENTE_NUEVO, headers=encabezado_de(admin))
    otro_email = {**DOCENTE_NUEVO, "email": "otro@docente.example.com"}

    respuesta = cliente.post("/usuarios", json=otro_email, headers=encabezado_de(admin))

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "USUARIO_DUPLICADO"


def test_email_repetido_sin_importar_mayusculas_responde_409(
    cliente: TestClient, admin: Usuario
) -> None:
    cliente.post("/usuarios", json=DOCENTE_NUEVO, headers=encabezado_de(admin))
    mismo_email = {
        **DOCENTE_NUEVO,
        "usuario": "100547203",
        "email": "Ricardo.Salinas@Docente.Example.com",
    }

    respuesta = cliente.post("/usuarios", json=mismo_email, headers=encabezado_de(admin))

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "EMAIL_DUPLICADO"


def test_docente_no_puede_administrar_usuarios(cliente: TestClient, sesion: Session) -> None:
    docente = nuevo_usuario()
    sesion.add(docente)
    sesion.commit()

    respuesta = cliente.post("/usuarios", json=DOCENTE_NUEVO, headers=encabezado_de(docente))

    assert respuesta.status_code == 403


def test_listar_filtra_por_rol(cliente: TestClient, sesion: Session, admin: Usuario) -> None:
    sesion.add(nuevo_usuario())  # docente
    sesion.commit()

    respuesta = cliente.get("/usuarios", params={"rol": "DOCENTE"}, headers=encabezado_de(admin))

    assert respuesta.status_code == 200
    assert [u["usuario"] for u in respuesta.json()] == ["100521347"]


def test_editar_solo_cambia_los_campos_enviados(
    cliente: TestClient, sesion: Session, admin: Usuario
) -> None:
    sesion.add(nuevo_usuario())
    sesion.commit()

    respuesta = cliente.patch(
        "/usuarios/100521347", json={"nombre": "Laura Isabel"}, headers=encabezado_de(admin)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Laura Isabel"
    assert respuesta.json()["apellidos"] == "Méndez Ortega"


def test_restablecer_contrasena_vuelve_al_numero_de_empleado(
    cliente: TestClient, sesion: Session, admin: Usuario
) -> None:
    sesion.add(nuevo_usuario())
    sesion.commit()

    cliente.patch(
        "/usuarios/100521347", json={"restablecer_contrasena": True}, headers=encabezado_de(admin)
    )

    login = cliente.post("/login", json={"usuario": "100521347", "contrasena": "100521347"})
    assert login.status_code == 200


def test_usuario_desactivado_ya_no_puede_entrar(
    cliente: TestClient, sesion: Session, admin: Usuario
) -> None:
    sesion.add(nuevo_usuario())
    sesion.commit()

    respuesta = cliente.delete("/usuarios/100521347", headers=encabezado_de(admin))

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    login = cliente.post("/login", json={"usuario": "100521347", "contrasena": CONTRASENA_PRUEBA})
    assert login.status_code == 403


def test_admin_no_puede_desactivarse_a_si_mismo(cliente: TestClient, admin: Usuario) -> None:
    respuesta = cliente.delete(f"/usuarios/{admin.usuario}", headers=encabezado_de(admin))

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "AUTODESACTIVACION"


def test_usuario_inexistente_responde_404(cliente: TestClient, admin: Usuario) -> None:
    respuesta = cliente.get("/usuarios/999999999", headers=encabezado_de(admin))

    assert respuesta.status_code == 404
