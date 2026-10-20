from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos import Calificacion, Categoria, Inscripcion, Materia, Tarea
from tests.fabricas import ALUMNO, DOCENTE, nueva_materia, nuevo_alumno

ANA = "202231045"  # la alumna del token ALUMNO
BRUNO = "202233918"


@pytest.fixture
def sitios_web(sesion: Session) -> Materia:
    """Sitios Web: Prácticas 40 % (Práctica 1 y 2) y Exámenes 60 % (Parcial 1).

    Ana tiene 100 en la Práctica 1 y 80 en el Parcial; la Práctica 2 está sin calificar.
    Bruno tiene 0 en todo (no debe afectar el promedio de Ana).
    """
    materia = nueva_materia()
    practicas = Categoria(nombre="Prácticas", peso=Decimal("40"))
    practicas.tareas.extend([Tarea(nombre="Práctica 1"), Tarea(nombre="Práctica 2")])
    examenes = Categoria(nombre="Exámenes", peso=Decimal("60"))
    examenes.tareas.append(Tarea(nombre="Parcial 1"))
    materia.categorias.extend([practicas, examenes])
    sesion.add_all(
        [materia, nuevo_alumno(), nuevo_alumno(matricula=BRUNO, nombre="Bruno", apellidos="Aguilar")]
    )
    sesion.flush()

    practica_1, _ = practicas.tareas
    parcial = examenes.tareas[0]
    sesion.add_all(
        [
            Inscripcion(nrc="48308", matricula=ANA),
            Inscripcion(nrc="48308", matricula=BRUNO),
            Calificacion(tarea_id=practica_1.id, matricula=ANA, puntos=Decimal("100")),
            Calificacion(tarea_id=parcial.id, matricula=ANA, puntos=Decimal("80")),
            Calificacion(tarea_id=practica_1.id, matricula=BRUNO, puntos=Decimal("0")),
            Calificacion(tarea_id=parcial.id, matricula=BRUNO, puntos=Decimal("0")),
        ]
    )
    sesion.commit()
    return materia


def test_mis_materias_con_mi_promedio_actual(
    cliente: TestClient, sesion: Session, sitios_web: Materia
) -> None:
    # Una segunda materia sin calificaciones todavía.
    sesion.add(nueva_materia(nrc="50130", nombre="Servicios Web"))
    sesion.flush()
    sesion.add(Inscripcion(nrc="50130", matricula=ANA))
    sesion.commit()

    respuesta = cliente.get("/mis-materias", headers=ALUMNO)

    assert respuesta.status_code == 200
    # (100 × 40 + 80 × 60) / 100 = 88 → 8.8. Las calificaciones de Bruno no cuentan.
    assert [(m["nombre"], m["promedio"]) for m in respuesta.json()] == [
        ("Desarrollo de Sitios Web", 8.8),
        ("Servicios Web", None),
    ]


def test_mis_calificaciones_por_categoria_y_tarea(cliente: TestClient, sitios_web: Materia) -> None:
    respuesta = cliente.get("/mis-materias/48308/calificaciones", headers=ALUMNO)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["promedio"] == 8.8
    practicas, examenes = cuerpo["categorias"]
    assert practicas["promedio"] == 100.0  # la Práctica 2 sin calificar no cuenta
    assert [(t["nombre"], t["puntos"]) for t in practicas["tareas"]] == [
        ("Práctica 1", 100.0),
        ("Práctica 2", None),
    ]
    assert examenes["promedio"] == 80.0


def test_materia_en_la_que_no_estoy_inscrito_responde_404(
    cliente: TestClient, sesion: Session, sitios_web: Materia
) -> None:
    sesion.add(nueva_materia(nrc="50130", nombre="Servicios Web"))
    sesion.commit()

    respuesta = cliente.get("/mis-materias/50130/calificaciones", headers=ALUMNO)

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "NO_INSCRITO"


def test_alumno_sin_materias_recibe_lista_vacia(cliente: TestClient) -> None:
    respuesta = cliente.get("/mis-materias", headers=ALUMNO)

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_un_docente_no_usa_las_rutas_del_alumno(cliente: TestClient) -> None:
    assert cliente.get("/mis-materias", headers=DOCENTE).status_code == 403
