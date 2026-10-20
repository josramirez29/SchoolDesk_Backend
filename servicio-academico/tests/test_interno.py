from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos import Inscripcion
from tests.conftest import CLAVE_INTERNA_PRUEBA
from tests.fabricas import nueva_materia, nuevo_alumno

CLAVE = {"X-Clave-Interna": CLAVE_INTERNA_PRUEBA}


def test_sin_clave_interna_responde_401(cliente: TestClient) -> None:
    respuesta = cliente.get("/interno/materias/48308")

    assert respuesta.status_code == 401


def test_materia_con_su_docente_titular(cliente: TestClient, sesion: Session) -> None:
    sesion.add(nueva_materia())
    sesion.commit()

    respuesta = cliente.get("/interno/materias/48308", headers=CLAVE)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "nrc": "48308",
        "nombre": "Desarrollo de Sitios Web",
        "num_empleado_docente": "100521347",
    }


def test_materia_inexistente_responde_404(cliente: TestClient) -> None:
    assert cliente.get("/interno/materias/99999", headers=CLAVE).status_code == 404


def test_alumno_inscrito_devuelve_su_nombre(cliente: TestClient, sesion: Session) -> None:
    sesion.add_all([nueva_materia(), nuevo_alumno()])
    sesion.flush()
    sesion.add(Inscripcion(nrc="48308", matricula="202231045"))
    sesion.commit()

    respuesta = cliente.get("/interno/materias/48308/alumnos/202231045", headers=CLAVE)

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Ana Sofía"


def test_alumno_no_inscrito_responde_404(cliente: TestClient, sesion: Session) -> None:
    sesion.add_all([nueva_materia(), nuevo_alumno()])
    sesion.commit()

    respuesta = cliente.get("/interno/materias/48308/alumnos/202231045", headers=CLAVE)

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "NO_INSCRITO"
