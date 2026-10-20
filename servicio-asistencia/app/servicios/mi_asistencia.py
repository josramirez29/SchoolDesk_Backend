"""Lo que ve el alumno: su asistencia en cada sesión de una materia.

La matrícula sale del token, nunca de la URL (igual que en academic).
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clientes.academico import ClienteAcademico
from app.esquemas import AsistenciaDeSesion, MiAsistencia
from app.modelos import Registro, Sesion


def obtener_mi_asistencia(
    bd: Session, cliente_academico: ClienteAcademico, matricula: str, nrc: str, ahora: datetime
) -> MiAsistencia:
    # Si no está inscrito, academic responde 404 NO_INSCRITO y se reenvía tal cual.
    # Sin esta validación, un alumno ajeno vería "FALTA" en todas las sesiones.
    cliente_academico.obtener_alumno_inscrito(nrc, matricula)

    sesiones = list(
        bd.scalars(select(Sesion).where(Sesion.nrc == nrc).order_by(Sesion.iniciada_en.desc()))
    )
    # Una sola consulta para los registros del alumno en todas esas sesiones (sin N+1).
    estados = {
        registro.sesion_id: registro.estado
        for registro in bd.scalars(
            select(Registro).where(
                Registro.matricula == matricula,
                Registro.sesion_id.in_([sesion.id for sesion in sesiones]),
            )
        )
    }

    filas = [
        AsistenciaDeSesion(
            sesion_id=sesion.id,
            iniciada_en=sesion.iniciada_en,
            estado=_estado(sesion, estados, ahora),
        )
        for sesion in sesiones
    ]
    conteo = [fila.estado for fila in filas]
    return MiAsistencia(
        nrc=nrc,
        presentes=conteo.count("PRESENTE"),
        retardos=conteo.count("RETARDO"),
        faltas=conteo.count("FALTA"),
        sesiones=filas,
    )


def _estado(sesion: Sesion, estados: dict[int, str], ahora: datetime) -> str:
    if sesion.id in estados:
        return estados[sesion.id]
    # Sin registro: es falta solo si la sesión ya terminó.
    return "EN_CURSO" if sesion.esta_activa(ahora) else "FALTA"
