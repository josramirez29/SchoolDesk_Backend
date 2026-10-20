from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos import Calificacion, Categoria, Inscripcion, Materia, Tarea
from tests.fabricas import nueva_materia, nuevo_alumno


def test_materia_con_categorias_tareas_y_calificacion(sesion: Session) -> None:
    materia = nueva_materia()
    practicas = Categoria(nombre="Prácticas", peso=Decimal("40"))
    practicas.tareas.append(Tarea(nombre="Práctica 3: Blog de café"))
    materia.categorias.append(practicas)
    sesion.add_all([nuevo_alumno(), materia])
    sesion.flush()
    sesion.add(
        Calificacion(tarea_id=practicas.tareas[0].id, matricula="202231045", puntos=Decimal("95.5"))
    )
    sesion.commit()

    guardada = sesion.get(Materia, "48308")

    assert guardada is not None
    assert guardada.categorias[0].peso == Decimal("40.00")
    calificacion = guardada.categorias[0].tareas[0].calificaciones[0]
    assert calificacion.puntos == Decimal("95.50")  # Decimal exacto, no 95.4999...


def test_inscribir_dos_veces_al_mismo_alumno_se_rechaza(sesion: Session) -> None:
    sesion.add_all([nuevo_alumno(), nueva_materia()])
    sesion.commit()
    sesion.add(Inscripcion(nrc="48308", matricula="202231045"))
    sesion.commit()

    sesion.add(Inscripcion(nrc="48308", matricula="202231045"))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_inscripcion_de_alumno_inexistente_se_rechaza(sesion: Session) -> None:
    sesion.add(nueva_materia())
    sesion.commit()

    sesion.add(Inscripcion(nrc="48308", matricula="999999999"))
    with pytest.raises(IntegrityError):  # llave foránea
        sesion.commit()


@pytest.mark.parametrize("peso", ["0", "-5", "100.01"])
def test_peso_fuera_de_rango_lo_rechaza_la_base(sesion: Session, peso: str) -> None:
    materia = nueva_materia()
    materia.categorias.append(Categoria(nombre="Exámenes", peso=Decimal(peso)))
    sesion.add(materia)

    with pytest.raises(IntegrityError):
        sesion.commit()


@pytest.mark.parametrize("puntos", ["-1", "100.5"])
def test_puntos_fuera_de_0_a_100_los_rechaza_la_base(sesion: Session, puntos: str) -> None:
    materia = nueva_materia()
    categoria = Categoria(nombre="Prácticas", peso=Decimal("100"))
    categoria.tareas.append(Tarea(nombre="Práctica 1"))
    materia.categorias.append(categoria)
    sesion.add_all([nuevo_alumno(), materia])
    sesion.flush()

    sesion.add(
        Calificacion(tarea_id=categoria.tareas[0].id, matricula="202231045", puntos=Decimal(puntos))
    )
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_borrar_una_categoria_borra_sus_tareas(sesion: Session) -> None:
    materia = nueva_materia()
    categoria = Categoria(nombre="Prácticas", peso=Decimal("100"))
    categoria.tareas.append(Tarea(nombre="Práctica 1"))
    materia.categorias.append(categoria)
    sesion.add(materia)
    sesion.commit()

    materia.categorias.remove(categoria)  # delete-orphan
    sesion.commit()

    assert sesion.scalar(select(func.count()).select_from(Tarea)) == 0
