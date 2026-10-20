"""Reporte de materia: calificaciones de academic + asistencia de servicio-asistencia."""

import logging
from dataclasses import asdict

from sqlalchemy.orm import Session

from app.calculo import calcular_asistencia, resumir_grupo
from app.clientes.asistencia import AsistenciaDeAlumno, ClienteAsistencia, ResumenAsistencia
from app.esquemas import (
    AsistenciaReporte,
    FilaReporte,
    MateriaRespuesta,
    ReporteMateria,
    ResumenGrupoReporte,
)
from app.servicios.calificaciones import obtener_concentrado
from app.servicios.materias import obtener_materia
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.seguridad import UsuarioActual

logger = logging.getLogger(__name__)

SIN_ASISTENCIAS = AsistenciaDeAlumno(presentes=0, retardos=0)


def generar_reporte(
    sesion: Session, cliente_asistencia: ClienteAsistencia, nrc: str, usuario: UsuarioActual
) -> ReporteMateria:
    concentrado = obtener_concentrado(sesion, nrc, usuario)  # también valida el acceso
    materia = obtener_materia(sesion, nrc)
    resumen_asistencia = _obtener_asistencia_si_se_puede(cliente_asistencia, nrc)

    filas = []
    for fila in concentrado.alumnos:
        asistencia = None
        if resumen_asistencia is not None:
            datos = resumen_asistencia.alumnos.get(fila.matricula, SIN_ASISTENCIAS)
            calculada = calcular_asistencia(
                resumen_asistencia.total_sesiones, datos.presentes, datos.retardos
            )
            asistencia = AsistenciaReporte(**asdict(calculada))
        filas.append(
            FilaReporte(
                matricula=fila.matricula,
                nombre=fila.nombre,
                apellidos=fila.apellidos,
                promedio=fila.promedio,
                asistencia=asistencia,
            )
        )

    resumen_grupo = resumir_grupo([fila.promedio for fila in concentrado.alumnos])
    return ReporteMateria(
        materia=MateriaRespuesta.model_validate(materia),
        asistencia_disponible=resumen_asistencia is not None,
        total_sesiones=resumen_asistencia.total_sesiones if resumen_asistencia else None,
        resumen=ResumenGrupoReporte(**asdict(resumen_grupo)),
        alumnos=filas,
    )


def _obtener_asistencia_si_se_puede(
    cliente_asistencia: ClienteAsistencia, nrc: str
) -> ResumenAsistencia | None:
    """Degradación elegante: si asistencia falla, el reporte sale sin esa parte.

    Las calificaciones no dependen de la asistencia; que un servicio caiga no
    debe impedir que el docente vea las calificaciones de su grupo.
    """
    try:
        return cliente_asistencia.obtener_resumen(nrc)
    except ErrorApp as error:
        logger.warning("Reporte de %s sin asistencia: %s", nrc, error.detalle)
        return None
