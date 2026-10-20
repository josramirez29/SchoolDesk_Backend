import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clientes.auth import Docente
from app.modelos import Alumno, Inscripcion, Materia
from schooldesk_comun.errores import ErrorApp
from tests.fabricas import ADMIN, DOCENTE, nueva_materia, nuevo_alumno
from tests.falsos import ClienteAuthFalso

# Los mismos archivos que se usarán en la demo.
DATOS_EJEMPLO = Path(__file__).parents[2] / "datos-ejemplo"


def importar(cliente: TestClient, tipo: str, contenido: bytes) -> Response:
    return cliente.post(
        f"/importar/{tipo}",
        files={"archivo": (f"{tipo}.csv", contenido, "text/csv")},
        headers=ADMIN,
    )


def ejemplo(nombre: str) -> bytes:
    return (DATOS_EJEMPLO / nombre).read_bytes()


def contar(sesion: Session, modelo: type) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


@pytest.fixture
def docentes_de_ejemplo(auth_falso: ClienteAuthFalso) -> None:
    """Hace que el auth falso conozca a los 8 docentes de datos-ejemplo/docentes.csv."""
    with open(DATOS_EJEMPLO / "docentes.csv", encoding="utf-8-sig") as archivo:
        auth_falso.docentes = [
            Docente(usuario=fila["num_empleado"], nombre=fila["nombre"], apellidos=fila["apellidos"])
            for fila in csv.DictReader(archivo)
        ]


# --- Alumnos ---


def test_importa_los_alumnos_de_ejemplo_con_una_sola_llamada_a_auth(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    respuesta = importar(cliente, "alumnos", ejemplo("alumnos.csv"))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"creados": 30, "omitidos": []}
    assert contar(sesion, Alumno) == 30
    assert auth_falso.llamadas_a_crear_cuentas == 1
    assert len(auth_falso.cuentas_creadas) == 30


def test_el_archivo_con_errores_de_la_demo_reporta_cada_fila(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    respuesta = importar(cliente, "alumnos", ejemplo("alumnos_con_errores.csv"))

    assert respuesta.status_code == 422
    assert respuesta.json()["filas"] == [
        {"fila": 3, "mensaje": "matricula tiene un formato inválido"},
        {"fila": 4, "mensaje": "nombre no puede estar vacío"},
        {"fila": 5, "mensaje": "email tiene un valor inválido"},
        {"fila": 6, "mensaje": "Fila repetida: ya aparece en la fila 2"},
    ]
    assert contar(sesion, Alumno) == 0
    assert auth_falso.llamadas_a_crear_cuentas == 0  # ni siquiera se llamó a auth


def test_email_en_uso_segun_auth_se_reporta_en_su_fila(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    auth_falso.error = ErrorApp(
        409, "EMAIL_EN_USO", "Correos en uso", {"emails": ["bruno.aguilar@alumno.example.com"]}
    )
    contenido = (
        "matricula,nombre,apellidos,email\n"
        "202231045,Ana Sofía,Acosta Bravo,ana.acosta@alumno.example.com\n"
        "202233918,Bruno,Aguilar Campos,bruno.aguilar@alumno.example.com\n"
    ).encode()

    respuesta = importar(cliente, "alumnos", contenido)

    assert respuesta.status_code == 422
    assert respuesta.json()["filas"] == [
        {"fila": 3, "mensaje": "El correo bruno.aguilar@alumno.example.com ya pertenece a otra cuenta"}
    ]
    assert contar(sesion, Alumno) == 0


def test_reimportar_alumnos_los_omite_sin_llamar_a_auth(
    cliente: TestClient, auth_falso: ClienteAuthFalso
) -> None:
    importar(cliente, "alumnos", ejemplo("alumnos.csv"))

    respuesta = importar(cliente, "alumnos", ejemplo("alumnos.csv"))

    assert respuesta.json()["creados"] == 0
    assert len(respuesta.json()["omitidos"]) == 30
    assert auth_falso.llamadas_a_crear_cuentas == 1  # solo la primera vez


# --- Materias ---


@pytest.mark.usefixtures("docentes_de_ejemplo")
def test_importa_las_materias_de_ejemplo_con_el_nombre_del_docente(
    cliente: TestClient, sesion: Session
) -> None:
    respuesta = importar(cliente, "materias", ejemplo("materias.csv"))

    assert respuesta.status_code == 200
    assert respuesta.json()["creados"] == 8
    assert sesion.get(Materia, "48308").nombre_docente == "Laura Méndez Ortega"


def test_materia_con_docente_desconocido_se_reporta(cliente: TestClient, sesion: Session) -> None:
    contenido = (
        "nrc,clave,nombre,seccion,num_empleado_docente\n"
        "48308,ITIS 702,Desarrollo de Sitios Web,001,100521347\n"
        "48011,ITIS 611,Arquitectura de Software,001,100599999\n"
    ).encode()

    respuesta = importar(cliente, "materias", contenido)

    assert respuesta.status_code == 422
    assert respuesta.json()["filas"] == [
        {"fila": 3, "mensaje": "No hay un docente activo con número de empleado 100599999"}
    ]
    assert contar(sesion, Materia) == 0


# --- Inscripciones ---


@pytest.mark.usefixtures("docentes_de_ejemplo")
def test_flujo_completo_de_la_demo(cliente: TestClient, sesion: Session) -> None:
    """Alumnos → materias → inscripciones, en el orden que seguirá el admin."""
    assert importar(cliente, "alumnos", ejemplo("alumnos.csv")).status_code == 200
    assert importar(cliente, "materias", ejemplo("materias.csv")).status_code == 200

    respuesta = importar(cliente, "inscripciones", ejemplo("inscripciones.csv"))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"creados": 103, "omitidos": []}
    inscritos_en_sitios_web = sesion.scalar(
        select(func.count()).select_from(Inscripcion).where(Inscripcion.nrc == "48308")
    )
    assert inscritos_en_sitios_web == 30


def test_inscripcion_con_materia_o_alumno_inexistente_se_reporta(
    cliente: TestClient, sesion: Session
) -> None:
    sesion.add_all([nueva_materia(), nuevo_alumno()])
    sesion.commit()
    contenido = (
        "nrc,matricula\n"
        "48308,202231045\n"
        "99999,202231045\n"
        "48308,202299999\n"
    ).encode()

    respuesta = importar(cliente, "inscripciones", contenido)

    assert respuesta.status_code == 422
    assert respuesta.json()["filas"] == [
        {"fila": 3, "mensaje": "No existe la materia con NRC 99999"},
        {"fila": 4, "mensaje": "No existe el alumno con matrícula 202299999"},
    ]
    assert contar(sesion, Inscripcion) == 0


def test_inscripcion_existente_se_omite(cliente: TestClient, sesion: Session) -> None:
    sesion.add_all([nueva_materia(), nuevo_alumno()])
    sesion.flush()
    sesion.add(Inscripcion(nrc="48308", matricula="202231045"))
    sesion.commit()

    respuesta = importar(cliente, "inscripciones", b"nrc,matricula\n48308,202231045\n")

    assert respuesta.json() == {
        "creados": 0,
        "omitidos": [{"fila": 2, "motivo": "El alumno ya está inscrito en esa materia"}],
    }


# --- Plantillas y permisos ---


def test_plantilla_de_alumnos(cliente: TestClient) -> None:
    respuesta = cliente.get("/importar/alumnos/plantilla")

    assert respuesta.status_code == 200
    assert respuesta.content.decode("utf-8") == "﻿matricula,nombre,apellidos,email\n"


def test_plantilla_de_tipo_desconocido_responde_422(cliente: TestClient) -> None:
    assert cliente.get("/importar/calificaciones/plantilla").status_code == 422


def test_docente_no_puede_importar(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/importar/alumnos",
        files={"archivo": ("alumnos.csv", ejemplo("alumnos.csv"), "text/csv")},
        headers=DOCENTE,
    )

    assert respuesta.status_code == 403
