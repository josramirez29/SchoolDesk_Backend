"""Consultas que hace servicio-academico (por /interno, con la clave interna)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.esquemas import AsistenciaDeAlumno, ResumenMateria
from app.modelos import EstadoAsistencia, Sesion


def resumen_de_materia(bd: Session, nrc: str, ahora: datetime) -> ResumenMateria:
    """Cuántas sesiones hubo y cuántas veces asistió cada alumno, para el reporte.

    Solo cuenta sesiones que ya terminaron: así nadie aparece con falta en el
    reporte mientras la sesión de hoy sigue abierta.

    Las faltas no se calculan aquí: academic las obtiene como
    total_sesiones - presentes - retardos, porque es quien conoce la lista de inscritos.
    """
    # selectinload trae los registros de todas las sesiones en una consulta extra
    # (y no una por sesión).
    consulta = select(Sesion).where(Sesion.nrc == nrc).options(selectinload(Sesion.registros))
    terminadas = [sesion for sesion in bd.scalars(consulta) if not sesion.esta_activa(ahora)]

    alumnos: dict[str, AsistenciaDeAlumno] = {}
    for sesion in terminadas:
        for registro in sesion.registros:
            conteo = alumnos.setdefault(registro.matricula, AsistenciaDeAlumno(presentes=0, retardos=0))
            if registro.estado == EstadoAsistencia.PRESENTE:
                conteo.presentes += 1
            else:
                conteo.retardos += 1

    return ResumenMateria(total_sesiones=len(terminadas), alumnos=alumnos)
