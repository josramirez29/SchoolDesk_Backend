"""El flujo completo: el docente abre la sesión, el alumno genera su QR y el docente lo escanea."""

from fastapi.testclient import TestClient
from redis import Redis

from app.clientes.academico import MateriaAcademica
from app.servicios.qr import PREFIJO_QR
from schooldesk_comun.roles import Rol
from tests.fabricas import ALUMNO, DOCENTE, OTRO_ALUMNO, OTRO_DOCENTE, encabezado_de
from tests.falsos import ClienteAcademicoFalso, RelojFalso

CAMILA_NO_INSCRITA = encabezado_de(Rol.ALUMNO, "202235502", "Camila Alvarado Díaz")


def abrir_sesion(cliente: TestClient, nrc: str = "48308") -> int:
    respuesta = cliente.post("/sesiones", json={"nrc": nrc}, headers=DOCENTE)
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def generar_qr(cliente: TestClient, alumno: dict[str, str] = ALUMNO, nrc: str = "48308") -> str:
    respuesta = cliente.post("/qr", json={"nrc": nrc}, headers=alumno)
    assert respuesta.status_code == 201, respuesta.json()
    return respuesta.json()["token"]


def escanear(
    cliente: TestClient, sesion_id: int, token: str, docente: dict[str, str] = DOCENTE
) -> dict:
    respuesta = cliente.post(
        f"/sesiones/{sesion_id}/escanear", json={"token": token}, headers=docente
    )
    return {"codigo": respuesta.status_code, **respuesta.json()}


# --- Generar el QR (alumno) ---


def test_el_qr_se_guarda_en_redis_y_expira_solo(cliente: TestClient, redis: Redis) -> None:
    sesion_id = abrir_sesion(cliente)

    respuesta = cliente.post("/qr", json={"nrc": "48308"}, headers=ALUMNO)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["segundos_de_vida"] == 30
    assert cuerpo["sesion_id"] == sesion_id
    assert 0 < redis.ttl(PREFIJO_QR + cuerpo["token"]) <= 30  # Redis lo borrará solo


def test_cada_qr_es_distinto(cliente: TestClient) -> None:
    abrir_sesion(cliente)

    assert generar_qr(cliente) != generar_qr(cliente)


def test_sin_sesion_abierta_no_hay_qr(cliente: TestClient) -> None:
    respuesta = cliente.post("/qr", json={"nrc": "48308"}, headers=ALUMNO)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "SIN_SESION_ACTIVA"


def test_alumno_no_inscrito_no_puede_generar_qr(cliente: TestClient) -> None:
    abrir_sesion(cliente)

    respuesta = cliente.post("/qr", json={"nrc": "48308"}, headers=CAMILA_NO_INSCRITA)

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "NO_INSCRITO"


def test_un_docente_no_genera_qr(cliente: TestClient) -> None:
    abrir_sesion(cliente)

    assert cliente.post("/qr", json={"nrc": "48308"}, headers=DOCENTE).status_code == 403


# --- Escanear (docente) ---


def test_escanear_en_los_primeros_5_minutos_es_presente(
    cliente: TestClient, reloj: RelojFalso
) -> None:
    sesion_id = abrir_sesion(cliente)
    reloj.avanzar(2)

    resultado = escanear(cliente, sesion_id, generar_qr(cliente))

    assert resultado["codigo"] == 201
    assert resultado["estado"] == "PRESENTE"
    assert resultado["nombre_alumno"] == "Ana Sofía Acosta Bravo"  # lo ve el docente
    detalle = cliente.get(f"/sesiones/{sesion_id}", headers=DOCENTE).json()
    assert [r["matricula"] for r in detalle["registros"]] == ["202231045"]


def test_escanear_despues_de_5_minutos_es_retardo(cliente: TestClient, reloj: RelojFalso) -> None:
    sesion_id = abrir_sesion(cliente)
    reloj.avanzar(7)

    resultado = escanear(cliente, sesion_id, generar_qr(cliente))

    assert resultado["estado"] == "RETARDO"


def test_el_mismo_qr_no_sirve_dos_veces(cliente: TestClient) -> None:
    """Anti-replay: alguien le toma foto al QR de Ana e intenta usarlo después."""
    sesion_id = abrir_sesion(cliente)
    token = generar_qr(cliente)
    escanear(cliente, sesion_id, token)

    resultado = escanear(cliente, sesion_id, token)

    assert resultado["codigo"] == 409
    assert resultado["error"] == "QR_INVALIDO"


def test_un_token_inventado_no_sirve(cliente: TestClient) -> None:
    sesion_id = abrir_sesion(cliente)

    resultado = escanear(cliente, sesion_id, "token-inventado")

    assert (resultado["codigo"], resultado["error"]) == (409, "QR_INVALIDO")


def test_un_qr_expirado_no_sirve(cliente: TestClient, redis: Redis) -> None:
    sesion_id = abrir_sesion(cliente)
    token = generar_qr(cliente)
    redis.delete(PREFIJO_QR + token)  # lo que hace Redis solo a los 30 s

    assert escanear(cliente, sesion_id, token)["error"] == "QR_INVALIDO"


def test_un_alumno_no_se_registra_dos_veces_con_dos_qr(cliente: TestClient) -> None:
    sesion_id = abrir_sesion(cliente)
    primero, segundo = generar_qr(cliente), generar_qr(cliente)  # ambos antes de escanear
    escanear(cliente, sesion_id, primero)

    resultado = escanear(cliente, sesion_id, segundo)

    assert (resultado["codigo"], resultado["error"]) == (409, "YA_REGISTRADO")


def test_ya_registrado_no_puede_generar_otro_qr(cliente: TestClient) -> None:
    sesion_id = abrir_sesion(cliente)
    escanear(cliente, sesion_id, generar_qr(cliente))

    respuesta = cliente.post("/qr", json={"nrc": "48308"}, headers=ALUMNO)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "YA_REGISTRADO"


def test_un_qr_de_otra_materia_no_sirve(
    cliente: TestClient, academico_falso: ClienteAcademicoFalso
) -> None:
    # Laura también da Servicios Web y tiene ahí una sesión abierta al mismo tiempo.
    academico_falso.materias["50130"] = MateriaAcademica(
        nrc="50130", nombre="Servicios Web", num_empleado_docente="100521347"
    )
    academico_falso.inscritos[("50130", "202231045")] = academico_falso.inscritos[
        ("48308", "202231045")
    ]
    sitios_web = abrir_sesion(cliente, "48308")
    abrir_sesion(cliente, "50130")
    token_de_servicios_web = generar_qr(cliente, nrc="50130")

    resultado = escanear(cliente, sitios_web, token_de_servicios_web)

    assert (resultado["codigo"], resultado["error"]) == (409, "QR_DE_OTRA_SESION")


def test_sesion_terminada_rechaza_el_escaneo_sin_gastar_el_qr(
    cliente: TestClient, redis: Redis, reloj: RelojFalso
) -> None:
    sesion_id = abrir_sesion(cliente)
    reloj.avanzar(9.5)
    token = generar_qr(cliente)
    reloj.avanzar(1)  # 10:30 → la sesión terminó

    resultado = escanear(cliente, sesion_id, token)

    assert (resultado["codigo"], resultado["error"]) == (409, "SESION_TERMINADA")
    assert redis.exists(PREFIJO_QR + token)  # el token no se consumió


def test_otro_docente_no_puede_escanear_y_no_gasta_el_qr(cliente: TestClient, redis: Redis) -> None:
    sesion_id = abrir_sesion(cliente)
    token = generar_qr(cliente)

    resultado = escanear(cliente, sesion_id, token, docente=OTRO_DOCENTE)

    assert resultado["codigo"] == 403
    assert redis.exists(PREFIJO_QR + token)
    assert escanear(cliente, sesion_id, token)["codigo"] == 201  # el titular sí puede


def test_varios_alumnos_en_la_misma_sesion(cliente: TestClient, reloj: RelojFalso) -> None:
    sesion_id = abrir_sesion(cliente)
    reloj.avanzar(1)
    escanear(cliente, sesion_id, generar_qr(cliente, ALUMNO))
    reloj.avanzar(5)
    escanear(cliente, sesion_id, generar_qr(cliente, OTRO_ALUMNO))

    detalle = cliente.get(f"/sesiones/{sesion_id}", headers=DOCENTE).json()

    assert (detalle["presentes"], detalle["retardos"]) == (1, 1)
    assert [r["nombre_alumno"] for r in detalle["registros"]] == [
        "Ana Sofía Acosta Bravo",
        "Bruno Aguilar Campos",
    ]
