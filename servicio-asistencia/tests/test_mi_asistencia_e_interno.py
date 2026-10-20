"""La asistencia del alumno y el resumen que usa academic para el reporte.

Escenario (todo en la materia 48308):
- Lunes:     Ana PRESENTE, Bruno RETARDO          (terminada)
- Miércoles: Ana RETARDO, Bruno no fue            (terminada)
- Hoy 9:00:  Ana PRESENTE, Bruno aún no llega     (abierta)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos import EstadoAsistencia, Registro, Sesion
from tests.claves import CLAVE_INTERNA_PRUEBA
from tests.fabricas import ALUMNO, DOCENTE, OTRO_ALUMNO, minutos_despues, nueva_sesion
from tests.falsos import RelojFalso

ANA, BRUNO = "202231045", "202233918"
DIA = 24 * 60  # minutos
CLAVE = {"X-Clave-Interna": CLAVE_INTERNA_PRUEBA}


def sesion_con(
    inicio: float, registros: dict[str, EstadoAsistencia], nrc: str = "48308"
) -> Sesion:
    sesion = nueva_sesion(
        nrc=nrc, iniciada_en=minutos_despues(inicio), termina_en=minutos_despues(inicio + 10)
    )
    sesion.registros.extend(
        Registro(
            matricula=matricula,
            nombre_alumno=matricula,
            estado=estado,
            registrado_en=minutos_despues(inicio + 1),
        )
        for matricula, estado in registros.items()
    )
    return sesion


@pytest.fixture
def semana(bd: Session) -> None:
    P, R = EstadoAsistencia.PRESENTE, EstadoAsistencia.RETARDO
    bd.add_all(
        [
            sesion_con(-4 * DIA, {ANA: P, BRUNO: R}),  # lunes
            sesion_con(-2 * DIA, {ANA: R}),  # miércoles
            sesion_con(0, {ANA: P}),  # hoy, sigue abierta (el reloj marca 9:00)
            # Otra materia: el registro de Ana aquí no debe aparecer en 48308.
            sesion_con(-DIA, {ANA: P}, nrc="50130"),
        ]
    )
    bd.commit()


# --- /mi-asistencia ---


@pytest.mark.usefixtures("semana")
def test_mi_asistencia_con_conteos(cliente: TestClient) -> None:
    respuesta = cliente.get("/mi-asistencia", params={"nrc": "48308"}, headers=ALUMNO)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [s["estado"] for s in cuerpo["sesiones"]] == ["PRESENTE", "RETARDO", "PRESENTE"]
    assert (cuerpo["presentes"], cuerpo["retardos"], cuerpo["faltas"]) == (2, 1, 0)


@pytest.mark.usefixtures("semana")
def test_sesion_abierta_sin_registro_es_en_curso_y_no_falta(cliente: TestClient) -> None:
    respuesta = cliente.get("/mi-asistencia", params={"nrc": "48308"}, headers=OTRO_ALUMNO)

    cuerpo = respuesta.json()
    assert [s["estado"] for s in cuerpo["sesiones"]] == ["EN_CURSO", "FALTA", "RETARDO"]
    assert cuerpo["faltas"] == 1


@pytest.mark.usefixtures("semana")
def test_cuando_la_sesion_termina_sin_registro_es_falta(
    cliente: TestClient, reloj: RelojFalso
) -> None:
    reloj.avanzar(15)

    respuesta = cliente.get("/mi-asistencia", params={"nrc": "48308"}, headers=OTRO_ALUMNO)

    assert respuesta.json()["sesiones"][0]["estado"] == "FALTA"


def test_alumno_no_inscrito_responde_404(cliente: TestClient) -> None:
    respuesta = cliente.get("/mi-asistencia", params={"nrc": "50130"}, headers=ALUMNO)

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "NO_INSCRITO"


def test_un_docente_no_usa_la_ruta_del_alumno(cliente: TestClient) -> None:
    assert cliente.get("/mi-asistencia", params={"nrc": "48308"}, headers=DOCENTE).status_code == 403


# --- /interno/materias/{nrc}/resumen ---


@pytest.mark.usefixtures("semana")
def test_resumen_solo_cuenta_sesiones_terminadas(cliente: TestClient) -> None:
    respuesta = cliente.get("/interno/materias/48308/resumen", headers=CLAVE)

    assert respuesta.status_code == 200
    # La de hoy sigue abierta: no cuenta (ni la sesión ni el PRESENTE de Ana).
    assert respuesta.json() == {
        "total_sesiones": 2,
        "alumnos": {
            ANA: {"presentes": 1, "retardos": 1},
            BRUNO: {"presentes": 0, "retardos": 1},
        },
    }


@pytest.mark.usefixtures("semana")
def test_al_terminar_la_sesion_de_hoy_ya_cuenta(cliente: TestClient, reloj: RelojFalso) -> None:
    reloj.avanzar(15)

    cuerpo = cliente.get("/interno/materias/48308/resumen", headers=CLAVE).json()

    assert cuerpo["total_sesiones"] == 3
    assert cuerpo["alumnos"][ANA] == {"presentes": 2, "retardos": 1}


def test_materia_sin_sesiones_devuelve_ceros(cliente: TestClient) -> None:
    cuerpo = cliente.get("/interno/materias/48308/resumen", headers=CLAVE).json()

    assert cuerpo == {"total_sesiones": 0, "alumnos": {}}


def test_resumen_sin_clave_interna_responde_401(cliente: TestClient) -> None:
    assert cliente.get("/interno/materias/48308/resumen").status_code == 401
