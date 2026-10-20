"""QR de un solo uso: el alumno lo genera y el docente lo escanea.

El token es aleatorio y opaco (no contiene datos). Lo que significa (de qué
sesión es y de qué alumno) se guarda en Redis con una vida de 30 segundos.
"""

import secrets
from datetime import datetime

from redis import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clientes.academico import ClienteAcademico
from app.configuracion import obtener_configuracion
from app.esquemas import DatosQr, QrGenerado, RegistroRespuesta
from app.modelos import Registro
from app.servicios.sesiones import buscar_sesion_activa, obtener_sesion_del_docente
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.seguridad import UsuarioActual

# Prefijo de las llaves: así se distinguen de cualquier otro uso de Redis.
PREFIJO_QR = "asistencia:qr:"


def generar_qr(
    bd: Session,
    redis: Redis,
    cliente_academico: ClienteAcademico,
    alumno: UsuarioActual,
    nrc: str,
    ahora: datetime,
) -> QrGenerado:
    sesion = buscar_sesion_activa(bd, nrc, ahora)
    if sesion is None:
        raise ErrorApp(409, "SIN_SESION_ACTIVA", "No hay una sesión de asistencia abierta para esta materia")

    # La inscripción se valida aquí, al generar, y no al escanear: el token dura
    # 30 s y queda ligado a esta matrícula, así se evita llamar a academic en el
    # momento de más carga (el docente escaneando a todo el grupo).
    inscrito = cliente_academico.obtener_alumno_inscrito(nrc, alumno.usuario)

    if bd.get(Registro, (sesion.id, alumno.usuario)) is not None:
        raise ErrorApp(409, "YA_REGISTRADO", "Ya tienes asistencia en esta sesión")

    # La matrícula sale del token JWT de quien lo pide: nadie puede generar
    # un QR a nombre de otro alumno.
    token = secrets.token_urlsafe(16)  # 128 bits aleatorios: imposible de adivinar
    datos = DatosQr(sesion_id=sesion.id, matricula=alumno.usuario, nombre=inscrito.nombre_completo)
    segundos = obtener_configuracion().segundos_vida_qr
    redis.set(PREFIJO_QR + token, datos.model_dump_json(), ex=segundos)  # ex = expira solo

    return QrGenerado(token=token, segundos_de_vida=segundos, sesion_id=sesion.id)


def escanear(
    bd: Session,
    redis: Redis,
    docente: UsuarioActual,
    sesion_id: int,
    token: str,
    ahora: datetime,
) -> RegistroRespuesta:
    # 1-2) Primero lo que NO gasta el token: si el docente se equivocó de sesión
    #      o la sesión ya terminó, el QR del alumno sigue sirviendo.
    sesion = obtener_sesion_del_docente(bd, sesion_id, docente)
    if not sesion.esta_activa(ahora):
        raise ErrorApp(409, "SESION_TERMINADA", "La sesión ya terminó")

    # 3) Anti-replay: GETDEL lee y BORRA el token en una sola operación atómica.
    #    Aunque el mismo QR se escanee dos veces al mismo tiempo, solo una
    #    lectura lo encuentra; la otra recibe None.
    crudo = redis.getdel(PREFIJO_QR + token)
    if crudo is None:
        raise ErrorApp(
            409, "QR_INVALIDO", "El QR expiró o ya se usó; pide al alumno que muestre uno nuevo"
        )
    datos = DatosQr.model_validate_json(crudo)

    # 4) Un QR generado para la sesión de otra materia no sirve aquí.
    if datos.sesion_id != sesion.id:
        raise ErrorApp(409, "QR_DE_OTRA_SESION", "Este QR es de otra sesión de asistencia")

    # 5) Un registro por alumno: se revisa antes para dar un mensaje claro...
    if bd.get(Registro, (sesion.id, datos.matricula)) is not None:
        raise ErrorApp(409, "YA_REGISTRADO", f"{datos.nombre} ya tiene asistencia en esta sesión")

    # 6) PRESENTE o RETARDO según la hora del escaneo.
    registro = Registro(
        sesion_id=sesion.id,
        matricula=datos.matricula,
        nombre_alumno=datos.nombre,
        estado=sesion.estado_para(ahora, obtener_configuracion().minutos_tolerancia),
        registrado_en=ahora,
    )
    bd.add(registro)
    try:
        bd.commit()
    except IntegrityError:
        # ...y la llave compuesta lo garantiza aunque dos QR del mismo alumno
        # se escaneen al mismo tiempo (el if de arriba no protege de eso).
        bd.rollback()
        raise ErrorApp(409, "YA_REGISTRADO", f"{datos.nombre} ya tiene asistencia en esta sesión")

    return RegistroRespuesta(
        matricula=registro.matricula,
        nombre_alumno=registro.nombre_alumno,
        estado=registro.estado,
        registrado_en=registro.registrado_en,
    )
