"""Rutas internas: solo las llama servicio-asistencia, con la clave X-Clave-Interna.

El gateway bloquea /interno/*, así que no se pueden llamar desde fuera.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.esquemas import AlumnoRespuesta, MateriaInterna
from app.modelos import Alumno, Materia
from app.servicios import interno
from schooldesk_comun.interno import requerir_clave_interna

router = APIRouter(
    prefix="/interno",
    tags=["Interno"],
    dependencies=[Depends(requerir_clave_interna)],  # aplica a todas las rutas de aquí
)


@router.get("/materias/{nrc}", response_model=MateriaInterna)
def obtener_materia(nrc: str, sesion: Session = Depends(obtener_sesion)) -> Materia:
    return interno.obtener_materia_interna(sesion, nrc)


@router.get("/materias/{nrc}/alumnos/{matricula}", response_model=AlumnoRespuesta)
def obtener_alumno_inscrito(
    nrc: str, matricula: str, sesion: Session = Depends(obtener_sesion)
) -> Alumno:
    return interno.obtener_alumno_inscrito(sesion, nrc, matricula)
