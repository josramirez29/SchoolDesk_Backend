from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos import Alumno, Inscripcion
from schooldesk_comun.errores import ErrorApp
from tests.fabricas import ADMIN, DOCENTE, nueva_materia, nuevo_alumno
from tests.falsos import ClienteAuthFalso

ANA = {
    "matricula": "202231045",
    "nombre": "Ana Sofía",
    "apellidos": "Acosta Bravo",
    "email": "Ana.Acosta@alumno.example.com",
}


def test_alta_crea_la_cuenta_en_auth_y_el_registro_academico(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    respuesta = cliente.post("/alumnos", json=ANA, headers=ADMIN)

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "matricula": "202231045",
        "nombre": "Ana Sofía",
        "apellidos": "Acosta Bravo",
    }
    assert sesion.get(Alumno, "202231045") is not None
    # A auth le llega el email (ya en minúsculas); academic no lo guarda.
    assert auth_falso.cuentas_creadas[0].email == "ana.acosta@alumno.example.com"


def test_si_auth_no_responde_no_se_guarda_nada(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    auth_falso.error = ErrorApp(503, "AUTH_NO_DISPONIBLE", "El servicio de cuentas no responde")

    respuesta = cliente.post("/alumnos", json=ANA, headers=ADMIN)

    assert respuesta.status_code == 503
    assert sesion.get(Alumno, "202231045") is None


def test_error_de_negocio_de_auth_llega_al_admin(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    auth_falso.error = ErrorApp(
        409,
        "EMAIL_EN_USO",
        "Algunos correos ya pertenecen a otra cuenta",
        {"emails": ["ana.acosta@alumno.example.com"]},
    )

    respuesta = cliente.post("/alumnos", json=ANA, headers=ADMIN)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "EMAIL_EN_USO"
    assert sesion.get(Alumno, "202231045") is None


def test_matricula_repetida_responde_409_sin_llamar_a_auth(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    sesion.add(nuevo_alumno())
    sesion.commit()

    respuesta = cliente.post("/alumnos", json=ANA, headers=ADMIN)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "ALUMNO_DUPLICADO"
    assert auth_falso.cuentas_creadas == []


def test_docente_no_puede_dar_de_alta_alumnos(cliente: TestClient) -> None:
    respuesta = cliente.post("/alumnos", json=ANA, headers=DOCENTE)

    assert respuesta.status_code == 403


def test_buscar_por_nombre_parcial_o_por_matricula(cliente: TestClient, sesion: Session) -> None:
    sesion.add_all(
        [
            nuevo_alumno(),
            nuevo_alumno(matricula="202233918", nombre="Bruno", apellidos="Aguilar Campos"),
        ]
    )
    sesion.commit()

    por_nombre = cliente.get("/alumnos", params={"buscar": "aguilar"}, headers=ADMIN)
    por_matricula = cliente.get("/alumnos", params={"buscar": "2022310"}, headers=ADMIN)
    todos = cliente.get("/alumnos", headers=ADMIN)

    assert [a["matricula"] for a in por_nombre.json()] == ["202233918"]
    assert [a["matricula"] for a in por_matricula.json()] == ["202231045"]
    assert [a["apellidos"] for a in todos.json()] == ["Acosta Bravo", "Aguilar Campos"]


def test_editar_el_nombre_lo_sincroniza_con_auth(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    sesion.add(nuevo_alumno())
    sesion.commit()

    respuesta = cliente.patch(
        "/alumnos/202231045", json={"apellidos": "Acosta Bravo de la Cruz"}, headers=ADMIN
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["apellidos"] == "Acosta Bravo de la Cruz"
    assert auth_falso.nombres_actualizados == [
        ("202231045", "Ana Sofía", "Acosta Bravo de la Cruz")
    ]


def test_si_auth_falla_al_editar_el_nombre_no_cambia(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    sesion.add(nuevo_alumno())
    sesion.commit()
    auth_falso.error = ErrorApp(503, "AUTH_NO_DISPONIBLE", "El servicio de cuentas no responde")

    respuesta = cliente.patch("/alumnos/202231045", json={"nombre": "Anita"}, headers=ADMIN)

    assert respuesta.status_code == 503
    sesion.expire_all()  # vuelve a leer de la base, no de la memoria de la sesión
    assert sesion.get(Alumno, "202231045").nombre == "Ana Sofía"


def test_detalle_incluye_sus_materias(cliente: TestClient, sesion: Session) -> None:
    sesion.add_all([nuevo_alumno(), nueva_materia()])
    sesion.flush()
    sesion.add(Inscripcion(nrc="48308", matricula="202231045"))
    sesion.commit()

    respuesta = cliente.get("/alumnos/202231045", headers=ADMIN)

    assert respuesta.status_code == 200
    assert respuesta.json()["materias"][0]["nombre"] == "Desarrollo de Sitios Web"


def test_alumno_inexistente_responde_404(cliente: TestClient) -> None:
    respuesta = cliente.get("/alumnos/202299999", headers=ADMIN)

    assert respuesta.status_code == 404
