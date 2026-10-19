from pathlib import Path

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos import Usuario
from schooldesk_comun.roles import Rol
from tests.fabricas import encabezado_de, nuevo_usuario

# El mismo archivo de ejemplo que se usará en la demo.
DOCENTES_EJEMPLO = Path(__file__).parents[2] / "datos-ejemplo" / "docentes.csv"


def importar(cliente: TestClient, admin: Usuario, contenido: bytes) -> Response:
    return cliente.post(
        "/importar/docentes",
        files={"archivo": ("docentes.csv", contenido, "text/csv")},
        headers=encabezado_de(admin),
    )


def contar_docentes(sesion: Session) -> int:
    return sesion.scalar(select(func.count()).where(Usuario.rol == Rol.DOCENTE))


def test_importa_el_archivo_de_ejemplo(cliente: TestClient, sesion: Session, admin: Usuario) -> None:
    respuesta = importar(cliente, admin, DOCENTES_EJEMPLO.read_bytes())

    assert respuesta.status_code == 200
    assert respuesta.json() == {"creados": 8, "omitidos": []}
    assert contar_docentes(sesion) == 8
    # Cada docente entra con su número de empleado como contraseña inicial.
    login = cliente.post("/login", json={"usuario": "100521347", "contrasena": "100521347"})
    assert login.status_code == 200
    assert login.json()["usuario"]["nombre"] == "Laura"


def test_importar_dos_veces_no_duplica(cliente: TestClient, sesion: Session, admin: Usuario) -> None:
    importar(cliente, admin, DOCENTES_EJEMPLO.read_bytes())

    respuesta = importar(cliente, admin, DOCENTES_EJEMPLO.read_bytes())

    assert respuesta.json()["creados"] == 0
    assert len(respuesta.json()["omitidos"]) == 8
    assert contar_docentes(sesion) == 8


def test_email_de_otra_cuenta_rechaza_todo_el_archivo(
    cliente: TestClient, sesion: Session, admin: Usuario
) -> None:
    contenido = (
        "num_empleado,nombre,apellidos,email\n"
        "100534812,Ricardo,Salinas Pérez,ricardo.salinas@docente.example.com\n"
        "100547203,Mónica,Herrera Castillo,admin@example.com\n"  # es el email del admin
    ).encode()

    respuesta = importar(cliente, admin, contenido)

    assert respuesta.status_code == 422
    assert respuesta.json()["filas"] == [
        {"fila": 3, "mensaje": "El correo admin@example.com ya pertenece a otra cuenta"}
    ]
    assert contar_docentes(sesion) == 0  # ni siquiera la fila 2, que era válida


def test_errores_de_formato_se_reportan_por_fila(
    cliente: TestClient, sesion: Session, admin: Usuario
) -> None:
    contenido = (
        "num_empleado,nombre,apellidos,email\n"
        "1005,Ricardo,Salinas Pérez,ricardo@docente.example.com\n"
        "100547203,Mónica,Herrera Castillo,no-es-un-correo\n"
    ).encode()

    respuesta = importar(cliente, admin, contenido)

    assert respuesta.status_code == 422
    assert [fila["fila"] for fila in respuesta.json()["filas"]] == [2, 3]
    assert contar_docentes(sesion) == 0


def test_docente_no_puede_importar(cliente: TestClient, sesion: Session) -> None:
    docente = nuevo_usuario()
    sesion.add(docente)
    sesion.commit()

    respuesta = importar(cliente, docente, DOCENTES_EJEMPLO.read_bytes())

    assert respuesta.status_code == 403


def test_plantilla_trae_los_encabezados_con_bom(cliente: TestClient) -> None:
    respuesta = cliente.get("/importar/docentes/plantilla")

    assert respuesta.status_code == 200
    assert respuesta.content.decode("utf-8") == "﻿num_empleado,nombre,apellidos,email\n"
