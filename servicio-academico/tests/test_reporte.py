from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.clientes.asistencia import AsistenciaDeAlumno, ResumenAsistencia
from app.modelos import Calificacion, Categoria, Inscripcion, Materia, Tarea
from schooldesk_comun.errores import ErrorApp
from tests.fabricas import ADMIN, DOCENTE, OTRO_DOCENTE, nueva_materia, nuevo_alumno
from tests.falsos import ClienteAsistenciaFalso

RUTA = "/materias/48308/reporte"
ANA = "202231045"
BRUNO = "202233918"
CAMILA = "202235502"


@pytest.fixture
def materia(sesion: Session) -> Materia:
    """Una categoría al 100 %. Ana tiene 95, Bruno 50 y Camila no tiene calificaciones."""
    materia = nueva_materia()
    categoria = Categoria(nombre="Proyecto", peso=Decimal("100"))
    categoria.tareas.append(Tarea(nombre="Entrega final"))
    materia.categorias.append(categoria)
    sesion.add_all(
        [
            materia,
            nuevo_alumno(),
            nuevo_alumno(matricula=BRUNO, nombre="Bruno", apellidos="Aguilar Campos"),
            nuevo_alumno(matricula=CAMILA, nombre="Camila", apellidos="Alvarado Díaz"),
        ]
    )
    sesion.flush()
    tarea_id = categoria.tareas[0].id
    sesion.add_all(
        [Inscripcion(nrc="48308", matricula=m) for m in (ANA, BRUNO, CAMILA)]
        + [
            Calificacion(tarea_id=tarea_id, matricula=ANA, puntos=Decimal("95")),
            Calificacion(tarea_id=tarea_id, matricula=BRUNO, puntos=Decimal("50")),
        ]
    )
    sesion.commit()
    return materia


def por_matricula(respuesta_json: dict) -> dict[str, dict]:
    return {fila["matricula"]: fila for fila in respuesta_json["alumnos"]}


@pytest.mark.usefixtures("materia")
def test_reporte_combina_calificaciones_y_asistencia(
    cliente: TestClient, asistencia_falso: ClienteAsistenciaFalso
) -> None:
    asistencia_falso.resumen = ResumenAsistencia(
        total_sesiones=10,
        alumnos={
            ANA: AsistenciaDeAlumno(presentes=7, retardos=1),
            BRUNO: AsistenciaDeAlumno(presentes=3, retardos=0),
            # Camila no asistió nunca: no viene en el resumen.
        },
    )

    respuesta = cliente.get(RUTA, headers=DOCENTE)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["asistencia_disponible"] is True
    assert cuerpo["total_sesiones"] == 10
    filas = por_matricula(cuerpo)
    assert filas[ANA]["promedio"] == 9.5
    assert filas[ANA]["asistencia"] == {
        "presentes": 7,
        "retardos": 1,
        "faltas": 2,
        "porcentaje": 80.0,
    }
    assert filas[CAMILA]["asistencia"] == {
        "presentes": 0,
        "retardos": 0,
        "faltas": 10,
        "porcentaje": 0.0,
    }


@pytest.mark.usefixtures("materia")
def test_resumen_del_grupo(cliente: TestClient) -> None:
    respuesta = cliente.get(RUTA, headers=DOCENTE)

    # Ana 9.5 aprueba, Bruno 5.0 reprueba, Camila sin calificaciones. Promedio (9.5+5)/2.
    assert respuesta.json()["resumen"] == {
        "promedio_grupo": 7.3,
        "aprobados": 1,
        "reprobados": 1,
        "sin_calificaciones": 1,
    }


@pytest.mark.usefixtures("materia")
def test_si_asistencia_esta_caida_el_reporte_sale_sin_asistencia(
    cliente: TestClient, asistencia_falso: ClienteAsistenciaFalso
) -> None:
    asistencia_falso.error = ErrorApp(503, "ASISTENCIA_NO_DISPONIBLE", "No responde")

    respuesta = cliente.get(RUTA, headers=ADMIN)

    assert respuesta.status_code == 200  # no falla el reporte completo
    cuerpo = respuesta.json()
    assert cuerpo["asistencia_disponible"] is False
    assert cuerpo["total_sesiones"] is None
    assert por_matricula(cuerpo)[ANA]["promedio"] == 9.5  # las calificaciones sí están
    assert all(fila["asistencia"] is None for fila in cuerpo["alumnos"])


@pytest.mark.usefixtures("materia")
def test_sin_sesiones_el_porcentaje_es_null(cliente: TestClient) -> None:
    respuesta = cliente.get(RUTA, headers=DOCENTE)  # el falso devuelve 0 sesiones

    assert por_matricula(respuesta.json())[ANA]["asistencia"]["porcentaje"] is None


@pytest.mark.usefixtures("materia")
def test_otro_docente_no_ve_el_reporte(cliente: TestClient) -> None:
    assert cliente.get(RUTA, headers=OTRO_DOCENTE).status_code == 403
