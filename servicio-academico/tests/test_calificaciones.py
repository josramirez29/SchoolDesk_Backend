from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos import Calificacion, Categoria, Inscripcion, Materia, Tarea
from tests.fabricas import DOCENTE, OTRO_DOCENTE, nueva_materia, nuevo_alumno

RUTA = "/materias/48308/calificaciones"
ANA = "202231045"
BRUNO = "202233918"


@pytest.fixture
def materia(sesion: Session) -> Materia:
    """Prácticas 40 % (Práctica 1 y 2) y Exámenes 60 % (Parcial 1), con Ana y Bruno inscritos."""
    materia = nueva_materia()
    practicas = Categoria(nombre="Prácticas", peso=Decimal("40"))
    practicas.tareas.extend([Tarea(nombre="Práctica 1"), Tarea(nombre="Práctica 2")])
    examenes = Categoria(nombre="Exámenes", peso=Decimal("60"))
    examenes.tareas.append(Tarea(nombre="Parcial 1"))
    materia.categorias.extend([practicas, examenes])
    sesion.add_all(
        [
            materia,
            nuevo_alumno(),  # Ana Acosta Bravo
            nuevo_alumno(matricula=BRUNO, nombre="Bruno", apellidos="Aguilar Campos"),
        ]
    )
    sesion.flush()
    sesion.add_all([Inscripcion(nrc="48308", matricula=ANA), Inscripcion(nrc="48308", matricula=BRUNO)])
    sesion.commit()
    return materia


def tareas(materia: Materia) -> tuple[int, int, int]:
    practica_1, practica_2 = (t.id for t in materia.categorias[0].tareas)
    return practica_1, practica_2, materia.categorias[1].tareas[0].id


def test_capturar_y_ver_el_promedio_en_el_concentrado(cliente: TestClient, materia: Materia) -> None:
    practica_1, practica_2, parcial = tareas(materia)
    entradas = [
        {"matricula": ANA, "tarea_id": practica_1, "puntos": 100},
        {"matricula": ANA, "tarea_id": practica_2, "puntos": 80},
        {"matricula": ANA, "tarea_id": parcial, "puntos": 80},
    ]

    respuesta = cliente.put(RUTA, json=entradas, headers=DOCENTE)

    assert respuesta.status_code == 200
    ana = respuesta.json()["alumnos"][0]
    assert ana["matricula"] == ANA
    assert ana["puntos"] == {str(practica_1): 100.0, str(practica_2): 80.0, str(parcial): 80.0}
    assert ana["promedio"] == 8.4  # el ejemplo del diseño


def test_alumno_sin_calificaciones_aparece_con_promedio_null(
    cliente: TestClient, materia: Materia
) -> None:
    respuesta = cliente.get(RUTA, headers=DOCENTE)

    filas = respuesta.json()["alumnos"]
    assert [f["apellidos"] for f in filas] == ["Acosta Bravo", "Aguilar Campos"]
    assert all(f["promedio"] is None for f in filas)
    assert all(valor is None for valor in filas[0]["puntos"].values())


def test_editar_una_calificacion_existente(cliente: TestClient, materia: Materia) -> None:
    practica_1, _, _ = tareas(materia)
    cliente.put(RUTA, json=[{"matricula": ANA, "tarea_id": practica_1, "puntos": 60}], headers=DOCENTE)

    respuesta = cliente.put(
        RUTA, json=[{"matricula": ANA, "tarea_id": practica_1, "puntos": 95.5}], headers=DOCENTE
    )

    assert respuesta.json()["alumnos"][0]["puntos"][str(practica_1)] == 95.5


def test_puntos_null_regresa_a_sin_calificar(
    cliente: TestClient, sesion: Session, materia: Materia
) -> None:
    practica_1, _, _ = tareas(materia)
    cliente.put(RUTA, json=[{"matricula": ANA, "tarea_id": practica_1, "puntos": 90}], headers=DOCENTE)

    respuesta = cliente.put(
        RUTA, json=[{"matricula": ANA, "tarea_id": practica_1, "puntos": None}], headers=DOCENTE
    )

    assert respuesta.json()["alumnos"][0]["promedio"] is None
    assert sesion.scalar(select(func.count()).select_from(Calificacion)) == 0


def test_alumno_no_inscrito_se_rechaza_y_no_se_guarda_nada(
    cliente: TestClient, sesion: Session, materia: Materia
) -> None:
    practica_1, _, _ = tareas(materia)
    entradas = [
        {"matricula": ANA, "tarea_id": practica_1, "puntos": 90},  # válida
        {"matricula": "202299999", "tarea_id": practica_1, "puntos": 100},  # no inscrito
    ]

    respuesta = cliente.put(RUTA, json=entradas, headers=DOCENTE)

    assert respuesta.status_code == 422
    assert respuesta.json()["errores"] == ["El alumno 202299999 no está inscrito en la materia"]
    assert sesion.scalar(select(func.count()).select_from(Calificacion)) == 0


def test_tarea_de_otra_materia_se_rechaza(
    cliente: TestClient, sesion: Session, materia: Materia
) -> None:
    otra = nueva_materia(nrc="50130", nombre="Servicios Web")
    categoria = Categoria(nombre="Prácticas", peso=Decimal("100"))
    categoria.tareas.append(Tarea(nombre="Ajena"))
    otra.categorias.append(categoria)
    sesion.add(otra)
    sesion.commit()

    respuesta = cliente.put(
        RUTA,
        json=[{"matricula": ANA, "tarea_id": categoria.tareas[0].id, "puntos": 90}],
        headers=DOCENTE,
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "CALIFICACIONES_INVALIDAS"


def test_puntos_fuera_de_rango_responden_422(cliente: TestClient, materia: Materia) -> None:
    practica_1, _, _ = tareas(materia)

    respuesta = cliente.put(
        RUTA, json=[{"matricula": ANA, "tarea_id": practica_1, "puntos": 101}], headers=DOCENTE
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "VALIDACION"


def test_otro_docente_no_ve_ni_captura(cliente: TestClient, materia: Materia) -> None:
    practica_1, _, _ = tareas(materia)

    ver = cliente.get(RUTA, headers=OTRO_DOCENTE)
    capturar = cliente.put(
        RUTA, json=[{"matricula": ANA, "tarea_id": practica_1, "puntos": 100}], headers=OTRO_DOCENTE
    )

    assert ver.status_code == 403
    assert capturar.status_code == 403
