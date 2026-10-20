"""Rutas de ponderaciones: categorías con peso y sus tareas (admin o docente titular)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.dependencias import admin_o_docente
from app.esquemas import CategoriaEntrada, CategoriaRespuesta, TareaEntrada, TareaRespuesta
from app.modelos import Categoria, Tarea
from app.servicios import ponderaciones
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/materias/{nrc}", tags=["Ponderaciones"])


@router.get("/categorias", response_model=list[CategoriaRespuesta])
def listar_categorias(
    nrc: str,
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> list[Categoria]:
    return ponderaciones.obtener_categorias(sesion, nrc, usuario)


@router.put("/categorias", response_model=list[CategoriaRespuesta])
def reemplazar_categorias(
    nrc: str,
    entradas: list[CategoriaEntrada],
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> list[Categoria]:
    return ponderaciones.reemplazar_categorias(sesion, nrc, usuario, entradas)


@router.post("/categorias/{categoria_id}/tareas", response_model=TareaRespuesta, status_code=201)
def crear_tarea(
    nrc: str,
    categoria_id: int,
    datos: TareaEntrada,
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> Tarea:
    return ponderaciones.crear_tarea(sesion, nrc, categoria_id, usuario, datos.nombre)


@router.patch("/tareas/{tarea_id}", response_model=TareaRespuesta)
def renombrar_tarea(
    nrc: str,
    tarea_id: int,
    datos: TareaEntrada,
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> Tarea:
    return ponderaciones.renombrar_tarea(sesion, nrc, tarea_id, usuario, datos.nombre)


@router.delete("/tareas/{tarea_id}", status_code=204)
def eliminar_tarea(
    nrc: str,
    tarea_id: int,
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
) -> None:
    ponderaciones.eliminar_tarea(sesion, nrc, tarea_id, usuario)
