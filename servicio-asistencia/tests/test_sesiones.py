from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.modelos import EstadoAsistencia, Registro
from schooldesk_comun.errores import ErrorApp
from tests.fabricas import ALUMNO, DOCENTE, OTRO_DOCENTE, minutos_despues, nueva_sesion
from tests.falsos import ClienteAcademicoFalso, RelojFalso


def abrir(cliente: TestClient, nrc: str = "48308", headers: dict[str, str] = DOCENTE) -> Response:
    return cliente.post("/sesiones", json={"nrc": nrc}, headers=headers)


def test_abrir_sesion_de_10_minutos(cliente: TestClient) -> None:
    respuesta = abrir(cliente)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["activa"] is True
    assert cuerpo["segundos_restantes"] == 600
    assert cuerpo["iniciada_en"].startswith("2026-10-19T09:00:00")
    assert cuerpo["termina_en"].startswith("2026-10-19T09:10:00")
    assert cuerpo["registros"] == []


def test_solo_el_titular_puede_abrir_sesion(cliente: TestClient) -> None:
    respuesta = abrir(cliente, headers=OTRO_DOCENTE)

    assert respuesta.status_code == 403
    assert respuesta.json()["error"] == "NO_ES_TU_MATERIA"


def test_materia_inexistente_en_academic_responde_404(cliente: TestClient) -> None:
    assert abrir(cliente, nrc="99999").status_code == 404


def test_si_academic_no_responde_no_se_abre_la_sesion(
    cliente: TestClient, academico_falso: ClienteAcademicoFalso
) -> None:
    academico_falso.error = ErrorApp(503, "ACADEMICO_NO_DISPONIBLE", "No responde")

    assert abrir(cliente).status_code == 503


def test_alumno_no_puede_abrir_sesion(cliente: TestClient) -> None:
    assert abrir(cliente, headers=ALUMNO).status_code == 403


def test_no_se_abren_dos_sesiones_a_la_vez(cliente: TestClient) -> None:
    primera = abrir(cliente).json()

    respuesta = abrir(cliente)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "SESION_ACTIVA"
    assert respuesta.json()["sesion_id"] == primera["id"]


def test_cuando_la_sesion_expira_se_puede_abrir_otra(
    cliente: TestClient, reloj: RelojFalso
) -> None:
    abrir(cliente)

    reloj.avanzar(11)  # 9:11: la primera ya terminó sola

    assert abrir(cliente).status_code == 201


def test_el_detalle_cuenta_el_tiempo_restante(cliente: TestClient, reloj: RelojFalso) -> None:
    sesion_id = abrir(cliente).json()["id"]

    reloj.avanzar(7.5)
    respuesta = cliente.get(f"/sesiones/{sesion_id}", headers=DOCENTE)

    assert respuesta.json()["segundos_restantes"] == 150


def test_otro_docente_no_ve_la_sesion(cliente: TestClient) -> None:
    sesion_id = abrir(cliente).json()["id"]

    respuesta = cliente.get(f"/sesiones/{sesion_id}", headers=OTRO_DOCENTE)

    assert respuesta.status_code == 403


def test_sesion_inexistente_responde_404(cliente: TestClient) -> None:
    assert cliente.get("/sesiones/999", headers=DOCENTE).status_code == 404


def test_cerrar_antes_de_tiempo(cliente: TestClient, reloj: RelojFalso) -> None:
    sesion_id = abrir(cliente).json()["id"]
    reloj.avanzar(3)

    respuesta = cliente.post(f"/sesiones/{sesion_id}/cerrar", headers=DOCENTE)

    assert respuesta.status_code == 200
    assert respuesta.json()["activa"] is False
    assert respuesta.json()["segundos_restantes"] == 0
    assert abrir(cliente).status_code == 201  # ya se puede abrir otra


def test_cerrar_una_sesion_terminada_responde_409(cliente: TestClient, reloj: RelojFalso) -> None:
    sesion_id = abrir(cliente).json()["id"]
    reloj.avanzar(10)

    respuesta = cliente.post(f"/sesiones/{sesion_id}/cerrar", headers=DOCENTE)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "SESION_TERMINADA"


def test_historial_de_la_mas_reciente_a_la_mas_antigua_con_conteos(
    cliente: TestClient, bd: Session, reloj: RelojFalso
) -> None:
    # Sesión del lunes con 1 presente y 1 retardo.
    lunes = nueva_sesion(iniciada_en=minutos_despues(-2880), termina_en=minutos_despues(-2870))
    lunes.registros.extend(
        [
            Registro(
                matricula="202231045",
                nombre_alumno="Ana Sofía Acosta Bravo",
                estado=EstadoAsistencia.PRESENTE,
                registrado_en=minutos_despues(-2879),
            ),
            Registro(
                matricula="202233918",
                nombre_alumno="Bruno Aguilar Campos",
                estado=EstadoAsistencia.RETARDO,
                registrado_en=minutos_despues(-2873),
            ),
        ]
    )
    bd.add_all([lunes, nueva_sesion(nrc="50130")])  # la segunda es de otra materia
    bd.commit()
    abrir(cliente)  # la de hoy

    respuesta = cliente.get("/sesiones", params={"nrc": "48308"}, headers=DOCENTE)

    historial = respuesta.json()
    assert len(historial) == 2
    assert historial[0]["activa"] is True  # hoy, primero
    assert (historial[1]["presentes"], historial[1]["retardos"]) == (1, 1)
