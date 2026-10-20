"""Consultas que hace servicio-asistencia (por /interno, con la clave interna)."""

from sqlalchemy.orm import Session

from app.modelos import Alumno, Inscripcion, Materia
from app.servicios.materias import obtener_materia
from schooldesk_comun.errores import ErrorApp


def obtener_materia_interna(sesion: Session, nrc: str) -> Materia:
    """Para que asistencia verifique que quien abre la sesión es el docente titular."""
    return obtener_materia(sesion, nrc)


def obtener_alumno_inscrito(sesion: Session, nrc: str, matricula: str) -> Alumno:
    """El alumno, solo si está inscrito en la materia.

    Asistencia lo usa al generar el QR y su nombre se muestra al docente al escanear.
    """
    inscripcion = sesion.get(Inscripcion, (nrc, matricula))
    if inscripcion is None:
        raise ErrorApp(
            404, "NO_INSCRITO", f"El alumno {matricula} no está inscrito en la materia {nrc}"
        )
    return inscripcion.alumno
