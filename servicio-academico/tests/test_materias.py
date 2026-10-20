from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos import Calificacion, Categoria, Inscripcion, Materia, Tarea
from schooldesk_comun.errores import ErrorApp
from tests.fabricas import ADMIN, ALUMNO, DOCENTE, OTRO_DOCENTE, nueva_materia, nuevo_alumno
from tests.falsos import ClienteAuthFalso

SITIOS_WEB = {
    "nrc": "48308",
    "clave": "ITIS 702",
    "nombre": "Desarrollo de Sitios Web",
    "seccion": "001",
    "num_empleado_docente": "100521347",
}


def guardar(sesion: Session, *objetos: object) -> None:
    sesion.add_all(objetos)
    sesion.commit()


# --- Materias ---


def test_alta_valida_al_docente_en_auth_y_guarda_su_nombre(cliente: TestClient, sesion: Session) -> None:
    respuesta = cliente.post("/materias", json=SITIOS_WEB, headers=ADMIN)

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre_docente"] == "Laura Méndez Ortega"
    assert sesion.get(Materia, "48308") is not None


def test_docente_que_no_existe_en_auth_se_rechaza(cliente: TestClient, sesion: Session) -> None:
    respuesta = cliente.post("/materias", json={**SITIOS_WEB, "num_empleado_docente": "100599999"}, headers=ADMIN)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "DOCENTE_NO_ENCONTRADO"
    assert sesion.get(Materia, "48308") is None


def test_nrc_repetido_responde_409(cliente: TestClient, sesion: Session) -> None:
    guardar(sesion, nueva_materia())

    respuesta = cliente.post("/materias", json=SITIOS_WEB, headers=ADMIN)

    assert respuesta.status_code == 409


def test_el_docente_solo_ve_sus_materias(cliente: TestClient, sesion: Session) -> None:
    guardar(
        sesion,
        nueva_materia(),  # de Laura
        nueva_materia(nrc="48011", nombre="Arquitectura de Software", num_empleado_docente="100534812"),
    )

    de_laura = cliente.get("/materias", headers=DOCENTE)
    del_admin = cliente.get("/materias", headers=ADMIN)

    assert [m["nrc"] for m in de_laura.json()] == ["48308"]
    assert len(del_admin.json()) == 2


def test_alumno_no_puede_listar_materias_aqui(cliente: TestClient) -> None:
    # El alumno tiene su propia ruta (/mis-materias) en otra parte.
    assert cliente.get("/materias", headers=ALUMNO).status_code == 403


def test_docente_no_puede_ver_materia_ajena(cliente: TestClient, sesion: Session) -> None:
    guardar(sesion, nueva_materia())

    respuesta = cliente.get("/materias/48308", headers=OTRO_DOCENTE)

    assert respuesta.status_code == 403
    assert respuesta.json()["error"] == "NO_ES_TU_MATERIA"


def test_cambiar_de_docente_actualiza_su_nombre(cliente: TestClient, sesion: Session) -> None:
    guardar(sesion, nueva_materia())

    respuesta = cliente.patch("/materias/48308", json={"num_empleado_docente": "100534812"}, headers=ADMIN)

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre_docente"] == "Ricardo Salinas Pérez"


def test_no_se_elimina_materia_con_alumnos(cliente: TestClient, sesion: Session) -> None:
    guardar(sesion, nuevo_alumno(), nueva_materia())
    guardar(sesion, Inscripcion(nrc="48308", matricula="202231045"))

    respuesta = cliente.delete("/materias/48308", headers=ADMIN)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "MATERIA_CON_ALUMNOS"


def test_eliminar_materia_sin_alumnos(cliente: TestClient, sesion: Session) -> None:
    guardar(sesion, nueva_materia())

    respuesta = cliente.delete("/materias/48308", headers=ADMIN)

    assert respuesta.status_code == 204
    sesion.expire_all()
    assert sesion.get(Materia, "48308") is None


def test_si_auth_no_responde_no_se_crea_la_materia(
    cliente: TestClient, sesion: Session, auth_falso: ClienteAuthFalso
) -> None:
    auth_falso.error = ErrorApp(503, "AUTH_NO_DISPONIBLE", "El servicio de cuentas no responde")

    respuesta = cliente.post("/materias", json=SITIOS_WEB, headers=ADMIN)

    assert respuesta.status_code == 503
    assert sesion.get(Materia, "48308") is None


# --- Inscripciones ---


def test_inscribir_y_listar_en_orden_de_apellidos(cliente: TestClient, sesion: Session) -> None:
    guardar(
        sesion,
        nueva_materia(),
        nuevo_alumno(matricula="202233918", nombre="Bruno", apellidos="Aguilar Campos"),
        nuevo_alumno(),  # Acosta Bravo
    )

    for matricula in ("202233918", "202231045"):
        respuesta = cliente.post("/materias/48308/alumnos", json={"matricula": matricula}, headers=ADMIN)
        assert respuesta.status_code == 201

    lista = cliente.get("/materias/48308/alumnos", headers=DOCENTE)
    assert [a["apellidos"] for a in lista.json()] == ["Acosta Bravo", "Aguilar Campos"]


def test_inscribir_dos_veces_responde_409(cliente: TestClient, sesion: Session) -> None:
    guardar(sesion, nueva_materia(), nuevo_alumno())
    cliente.post("/materias/48308/alumnos", json={"matricula": "202231045"}, headers=ADMIN)

    respuesta = cliente.post("/materias/48308/alumnos", json={"matricula": "202231045"}, headers=ADMIN)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "YA_INSCRITO"


def test_inscribir_alumno_inexistente_responde_404(cliente: TestClient, sesion: Session) -> None:
    guardar(sesion, nueva_materia())

    respuesta = cliente.post("/materias/48308/alumnos", json={"matricula": "202299999"}, headers=ADMIN)

    assert respuesta.status_code == 404


def test_dar_de_baja_alumno_sin_calificaciones(cliente: TestClient, sesion: Session) -> None:
    guardar(sesion, nueva_materia(), nuevo_alumno())
    guardar(sesion, Inscripcion(nrc="48308", matricula="202231045"))

    respuesta = cliente.delete("/materias/48308/alumnos/202231045", headers=ADMIN)

    assert respuesta.status_code == 204


def test_no_se_da_de_baja_alumno_con_calificaciones(cliente: TestClient, sesion: Session) -> None:
    materia = nueva_materia()
    categoria = Categoria(nombre="Prácticas", peso=Decimal("100"))
    categoria.tareas.append(Tarea(nombre="Práctica 1"))
    materia.categorias.append(categoria)
    guardar(sesion, materia, nuevo_alumno())
    guardar(
        sesion,
        Inscripcion(nrc="48308", matricula="202231045"),
        Calificacion(tarea_id=categoria.tareas[0].id, matricula="202231045", puntos=Decimal("90")),
    )

    respuesta = cliente.delete("/materias/48308/alumnos/202231045", headers=ADMIN)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "ALUMNO_CON_CALIFICACIONES"
