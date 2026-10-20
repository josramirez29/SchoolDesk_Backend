"""Sesiones de asistencia del docente: abrir, consultar, cerrar e historial.

`ahora` llega como parámetro (no se lee del sistema) para que las reglas de
tiempo se puedan probar sin esperar.
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clientes.academico import ClienteAcademico
from app.configuracion import obtener_configuracion
from app.esquemas import RegistroRespuesta, SesionDetalle, SesionResumen
from app.modelos import EstadoAsistencia, Sesion
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.seguridad import UsuarioActual


def abrir_sesion(
    bd: Session,
    cliente_academico: ClienteAcademico,
    docente: UsuarioActual,
    nrc: str,
    ahora: datetime,
) -> SesionDetalle:
    # academic es la fuente de verdad de quién es el titular de la materia.
    materia = cliente_academico.obtener_materia(nrc)
    if materia.num_empleado_docente != docente.usuario:
        raise ErrorApp(403, "NO_ES_TU_MATERIA", "Solo el docente titular puede tomar asistencia")

    activa = buscar_sesion_activa(bd, nrc, ahora)
    if activa is not None:
        raise ErrorApp(
            409,
            "SESION_ACTIVA",
            "Ya hay una sesión de asistencia abierta para esta materia",
            extra={"sesion_id": activa.id},  # para que el frontend pueda ir a ella
        )

    minutos = obtener_configuracion().minutos_sesion
    sesion = Sesion(
        nrc=nrc,
        num_empleado_docente=docente.usuario,
        iniciada_en=ahora,
        termina_en=ahora + timedelta(minutes=minutos),
    )
    bd.add(sesion)
    bd.commit()
    return detalle(sesion, ahora)


def obtener_sesion_del_docente(bd: Session, sesion_id: int, docente: UsuarioActual) -> Sesion:
    sesion = bd.get(Sesion, sesion_id)
    if sesion is None:
        raise ErrorApp(404, "SESION_NO_ENCONTRADA", "La sesión de asistencia no existe")
    if sesion.num_empleado_docente != docente.usuario:
        raise ErrorApp(403, "NO_ES_TU_SESION", "Esta sesión la abrió otro docente")
    return sesion


def cerrar_sesion(bd: Session, sesion_id: int, docente: UsuarioActual, ahora: datetime) -> SesionDetalle:
    sesion = obtener_sesion_del_docente(bd, sesion_id, docente)
    if not sesion.esta_activa(ahora):
        raise ErrorApp(409, "SESION_TERMINADA", "La sesión ya terminó")
    sesion.cerrada_en = ahora
    bd.commit()
    return detalle(sesion, ahora)


def listar_sesiones(
    bd: Session, nrc: str, docente: UsuarioActual, ahora: datetime
) -> list[SesionResumen]:
    """Historial de la materia, de la más reciente a la más antigua."""
    consulta = (
        select(Sesion)
        .where(Sesion.nrc == nrc, Sesion.num_empleado_docente == docente.usuario)
        .order_by(Sesion.iniciada_en.desc())
    )
    return [resumen(sesion, ahora) for sesion in bd.scalars(consulta)]


def buscar_sesion_activa(bd: Session, nrc: str, ahora: datetime) -> Sesion | None:
    """La sesión abierta de la materia, si hay. También la usa la generación de QR."""
    consulta = select(Sesion).where(
        Sesion.nrc == nrc,
        Sesion.cerrada_en.is_(None),
        Sesion.termina_en > ahora,
    )
    return bd.scalars(consulta).first()


# --- Conversión a respuesta (agrega los campos que dependen de la hora) ---


def resumen(sesion: Sesion, ahora: datetime) -> SesionResumen:
    estados = [registro.estado for registro in sesion.registros]
    return SesionResumen(
        id=sesion.id,
        nrc=sesion.nrc,
        iniciada_en=sesion.iniciada_en,
        termina_en=sesion.termina_en,
        cerrada_en=sesion.cerrada_en,
        activa=sesion.esta_activa(ahora),
        segundos_restantes=sesion.segundos_restantes(ahora),
        presentes=estados.count(EstadoAsistencia.PRESENTE),
        retardos=estados.count(EstadoAsistencia.RETARDO),
    )


def detalle(sesion: Sesion, ahora: datetime) -> SesionDetalle:
    return SesionDetalle(
        **resumen(sesion, ahora).model_dump(),
        registros=[
            RegistroRespuesta(
                matricula=registro.matricula,
                nombre_alumno=registro.nombre_alumno,
                estado=registro.estado,
                registrado_en=registro.registrado_en,
            )
            for registro in sesion.registros
        ],
    )
