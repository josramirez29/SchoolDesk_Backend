from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos import Alumno, Calificacion, Categoria, Inscripcion, Materia, Tarea
from tests.fabricas import DOCENTE, OTRO_DOCENTE, nueva_materia, nuevo_alumno

RUTA = "/materias/48308/categorias"


@pytest.fixture
def materia(sesion: Session) -> Materia:
    """Desarrollo de Sitios Web con Prácticas (40 %, con una tarea) y Exámenes (60 %)."""
    materia = nueva_materia()
    practicas = Categoria(nombre="Prácticas", peso=Decimal("40"))
    practicas.tareas.append(Tarea(nombre="Práctica 1"))
    materia.categorias.extend([practicas, Categoria(nombre="Exámenes", peso=Decimal("60"))])
    sesion.add(materia)
    sesion.commit()
    return materia


def ids_por_nombre(cliente: TestClient) -> dict[str, int]:
    return {c["nombre"]: c["id"] for c in cliente.get(RUTA, headers=DOCENTE).json()}


def calificar(sesion: Session, tarea: Tarea, alumno: Alumno) -> None:
    sesion.add_all([alumno, Inscripcion(nrc="48308", matricula=alumno.matricula)])
    sesion.flush()
    sesion.add(Calificacion(tarea_id=tarea.id, matricula=alumno.matricula, puntos=Decimal("90")))
    sesion.commit()


# --- Categorías ---


def test_crear_categorias_y_ver_el_peso_como_numero(cliente: TestClient, sesion: Session) -> None:
    sesion.add(nueva_materia())
    sesion.commit()
    lista = [
        {"nombre": "Prácticas", "peso": 40},
        {"nombre": "Exámenes", "peso": 35.5},
        {"nombre": "Proyecto", "peso": 24.5},
    ]

    respuesta = cliente.put(RUTA, json=lista, headers=DOCENTE)

    assert respuesta.status_code == 200
    assert [(c["nombre"], c["peso"]) for c in respuesta.json()] == [
        ("Prácticas", 40.0),
        ("Exámenes", 35.5),
        ("Proyecto", 24.5),
    ]


def test_pesos_que_no_suman_100_se_rechazan(cliente: TestClient, materia: Materia) -> None:
    lista = [{"nombre": "Prácticas", "peso": 40}, {"nombre": "Exámenes", "peso": 50}]

    respuesta = cliente.put(RUTA, json=lista, headers=DOCENTE)

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "error": "PESOS_NO_SUMAN_100",
        "detalle": "Los pesos deben sumar 100; ahora suman 90",
    }


def test_nombres_repetidos_sin_importar_mayusculas_se_rechazan(
    cliente: TestClient, materia: Materia
) -> None:
    lista = [{"nombre": "Prácticas", "peso": 50}, {"nombre": "prácticas", "peso": 50}]

    respuesta = cliente.put(RUTA, json=lista, headers=DOCENTE)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "NOMBRES_REPETIDOS"


def test_editar_por_id_conserva_la_categoria_y_sus_tareas(
    cliente: TestClient, materia: Materia
) -> None:
    ids = ids_por_nombre(cliente)
    lista = [
        {"id": ids["Prácticas"], "nombre": "Prácticas de clase", "peso": 50},
        {"id": ids["Exámenes"], "nombre": "Exámenes", "peso": 50},
    ]

    respuesta = cliente.put(RUTA, json=lista, headers=DOCENTE)

    practicas = respuesta.json()[0]
    assert practicas["id"] == ids["Prácticas"]
    assert practicas["nombre"] == "Prácticas de clase"
    assert [t["nombre"] for t in practicas["tareas"]] == ["Práctica 1"]


def test_quitar_categoria_sin_calificaciones_la_borra_con_sus_tareas(
    cliente: TestClient, sesion: Session, materia: Materia
) -> None:
    ids = ids_por_nombre(cliente)

    respuesta = cliente.put(
        RUTA, json=[{"id": ids["Exámenes"], "nombre": "Exámenes", "peso": 100}], headers=DOCENTE
    )

    assert respuesta.status_code == 200
    assert sesion.scalar(select(func.count()).select_from(Tarea)) == 0


def test_no_se_quita_una_categoria_con_calificaciones(
    cliente: TestClient, sesion: Session, materia: Materia
) -> None:
    calificar(sesion, materia.categorias[0].tareas[0], nuevo_alumno())
    ids = ids_por_nombre(cliente)

    respuesta = cliente.put(
        RUTA, json=[{"id": ids["Exámenes"], "nombre": "Exámenes", "peso": 100}], headers=DOCENTE
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "CATEGORIA_CON_CALIFICACIONES"
    assert len(ids_por_nombre(cliente)) == 2  # no cambió nada


def test_se_puede_reusar_el_nombre_de_una_categoria_quitada(
    cliente: TestClient, materia: Materia
) -> None:
    # Se quita "Prácticas" y, en la misma petición, "Exámenes" pasa a llamarse "Prácticas".
    ids = ids_por_nombre(cliente)

    respuesta = cliente.put(
        RUTA, json=[{"id": ids["Exámenes"], "nombre": "Prácticas", "peso": 100}], headers=DOCENTE
    )

    assert respuesta.status_code == 200
    assert [c["nombre"] for c in respuesta.json()] == ["Prácticas"]


def test_id_de_otra_materia_se_rechaza(
    cliente: TestClient, sesion: Session, materia: Materia
) -> None:
    otra = nueva_materia(nrc="50130", nombre="Servicios Web")
    otra.categorias.append(Categoria(nombre="Ajena", peso=Decimal("100")))
    sesion.add(otra)
    sesion.commit()

    respuesta = cliente.put(
        RUTA, json=[{"id": otra.categorias[0].id, "nombre": "Ajena", "peso": 100}], headers=DOCENTE
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "CATEGORIA_AJENA"


def test_otro_docente_no_puede_cambiar_las_ponderaciones(
    cliente: TestClient, materia: Materia
) -> None:
    respuesta = cliente.put(RUTA, json=[{"nombre": "Todo", "peso": 100}], headers=OTRO_DOCENTE)

    assert respuesta.status_code == 403


# --- Tareas ---


def test_crear_tarea_en_una_categoria(cliente: TestClient, materia: Materia) -> None:
    ids = ids_por_nombre(cliente)

    respuesta = cliente.post(
        f"{RUTA}/{ids['Prácticas']}/tareas",
        json={"nombre": "Práctica 3: Blog de café"},
        headers=DOCENTE,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "Práctica 3: Blog de café"


def test_tarea_con_nombre_repetido_en_la_categoria_responde_409(
    cliente: TestClient, materia: Materia
) -> None:
    ids = ids_por_nombre(cliente)

    respuesta = cliente.post(
        f"{RUTA}/{ids['Prácticas']}/tareas", json={"nombre": "práctica 1"}, headers=DOCENTE
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "TAREA_DUPLICADA"


def test_renombrar_tarea(cliente: TestClient, materia: Materia) -> None:
    tarea_id = materia.categorias[0].tareas[0].id

    respuesta = cliente.patch(
        f"/materias/48308/tareas/{tarea_id}", json={"nombre": "Práctica 1: HTML"}, headers=DOCENTE
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Práctica 1: HTML"


def test_no_se_elimina_una_tarea_con_calificaciones(
    cliente: TestClient, sesion: Session, materia: Materia
) -> None:
    tarea = materia.categorias[0].tareas[0]
    calificar(sesion, tarea, nuevo_alumno())

    respuesta = cliente.delete(f"/materias/48308/tareas/{tarea.id}", headers=DOCENTE)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "TAREA_CON_CALIFICACIONES"


def test_eliminar_tarea_sin_calificaciones(cliente: TestClient, materia: Materia) -> None:
    tarea_id = materia.categorias[0].tareas[0].id

    respuesta = cliente.delete(f"/materias/48308/tareas/{tarea_id}", headers=DOCENTE)

    assert respuesta.status_code == 204


def test_tarea_de_otra_materia_responde_404(
    cliente: TestClient, sesion: Session, materia: Materia
) -> None:
    otra = nueva_materia(nrc="50130", nombre="Servicios Web")
    categoria = Categoria(nombre="Prácticas", peso=Decimal("100"))
    categoria.tareas.append(Tarea(nombre="Ajena"))
    otra.categorias.append(categoria)
    sesion.add(otra)
    sesion.commit()

    # Laura es titular de ambas, pero la tarea no pertenece a la materia de la ruta.
    respuesta = cliente.delete(f"/materias/48308/tareas/{categoria.tareas[0].id}", headers=DOCENTE)

    assert respuesta.status_code == 404
