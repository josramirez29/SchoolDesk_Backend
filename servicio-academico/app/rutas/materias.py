"""Rutas de materias e inscripciones."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.clientes.auth import ClienteAuth
from app.dependencias import admin_o_docente, obtener_cliente_auth, solo_admin
from app.esquemas import (
    AlumnoRespuesta,
    InscripcionNueva,
    MateriaEdicion,
    MateriaNueva,
    MateriaRespuesta,
)
from app.modelos import Alumno, Materia
from app.servicios import materias
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/materias", tags=["Materias"])


@router.get("", response_model=list[MateriaRespuesta])
def listar(
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> list[Materia]:
    return materias.listar_materias(sesion, usuario)


@router.post("", response_model=MateriaRespuesta, status_code=201)
def crear(
    datos: MateriaNueva,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
    cliente_auth: ClienteAuth = Depends(obtener_cliente_auth),
) -> Materia:
    return materias.crear_materia(sesion, cliente_auth, datos)


@router.get("/{nrc}", response_model=MateriaRespuesta)
def obtener(
    nrc: str,
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> Materia:
    return materias.obtener_materia_con_acceso(sesion, nrc, usuario)


@router.patch("/{nrc}", response_model=MateriaRespuesta)
def editar(
    nrc: str,
    datos: MateriaEdicion,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
    cliente_auth: ClienteAuth = Depends(obtener_cliente_auth),
) -> Materia:
    return materias.editar_materia(sesion, cliente_auth, nrc, datos)


@router.delete("/{nrc}", status_code=204)
def eliminar(
    nrc: str,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> None:
    materias.eliminar_materia(sesion, nrc)


@router.get("/{nrc}/alumnos", response_model=list[AlumnoRespuesta])
def listar_inscritos(
    nrc: str,
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> list[Alumno]:
    return materias.listar_inscritos(sesion, nrc, usuario)


@router.post("/{nrc}/alumnos", response_model=AlumnoRespuesta, status_code=201)
def inscribir(
    nrc: str,
    datos: InscripcionNueva,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> Alumno:
    return materias.inscribir(sesion, nrc, datos.matricula)


@router.delete("/{nrc}/alumnos/{matricula}", status_code=204)
def dar_de_baja(
    nrc: str,
    matricula: str,
    _: UsuarioActual = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
) -> None:
    materias.dar_de_baja(sesion, nrc, matricula)
