"""Rutas del alumno. Todas exigen rol ALUMNO y usan la matrícula del token."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.dependencias import solo_alumno
from app.esquemas import MiMateria, MisCalificaciones
from app.servicios import mis_materias
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/mis-materias", tags=["Alumno"])


@router.get("", response_model=list[MiMateria])
def listar(
    alumno: UsuarioActual = Depends(solo_alumno),
    sesion: Session = Depends(obtener_sesion),
) -> list[MiMateria]:
    return mis_materias.listar_mis_materias(sesion, alumno.usuario)


@router.get("/{nrc}/calificaciones", response_model=MisCalificaciones)
def calificaciones(
    nrc: str,
    alumno: UsuarioActual = Depends(solo_alumno),
    sesion: Session = Depends(obtener_sesion),
) -> MisCalificaciones:
    return mis_materias.obtener_mis_calificaciones(sesion, alumno.usuario, nrc)
