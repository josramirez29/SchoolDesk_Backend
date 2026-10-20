"""Ponderaciones de una materia: categorías con peso y las tareas de cada una."""

from decimal import Decimal

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.esquemas import CategoriaEntrada
from app.modelos import Calificacion, Categoria, Materia, Tarea
from app.servicios.materias import obtener_materia_con_acceso
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.seguridad import UsuarioActual

SUMA_REQUERIDA = Decimal("100")


# --- Categorías ---


def obtener_categorias(sesion: Session, nrc: str, usuario: UsuarioActual) -> list[Categoria]:
    return obtener_materia_con_acceso(sesion, nrc, usuario).categorias


def reemplazar_categorias(
    sesion: Session, nrc: str, usuario: UsuarioActual, entradas: list[CategoriaEntrada]
) -> list[Categoria]:
    """Guarda la lista completa de categorías de la materia.

    Se reemplaza la lista entera (y no categoría por categoría) porque "los pesos
    suman 100" es una regla del conjunto: editando de una en una, la suma sería
    inválida en algún paso intermedio.
    """
    materia = obtener_materia_con_acceso(sesion, nrc, usuario)
    _validar_lista(entradas)

    actuales = {categoria.id: categoria for categoria in materia.categorias}
    ids_enviados = {entrada.id for entrada in entradas if entrada.id is not None}
    if ids_enviados - actuales.keys():
        raise ErrorApp(
            422, "CATEGORIA_AJENA", "La lista incluye categorías que no son de esta materia"
        )

    a_quitar = [categoria for id_, categoria in actuales.items() if id_ not in ids_enviados]
    con_calificaciones = [
        categoria.nombre
        for categoria in a_quitar
        if _categoria_tiene_calificaciones(sesion, categoria.id)
    ]
    if con_calificaciones:
        raise ErrorApp(
            409,
            "CATEGORIA_CON_CALIFICACIONES",
            "No se pueden quitar categorías que ya tienen calificaciones: "
            + ", ".join(con_calificaciones),
        )

    for categoria in a_quitar:
        materia.categorias.remove(categoria)  # sus tareas se borran en cascada
    # Se borran primero para liberar sus nombres: así se puede quitar "Tareas" y
    # renombrar otra categoría a "Tareas" en la misma petición.
    sesion.flush()

    for entrada in entradas:
        if entrada.id is None:
            materia.categorias.append(Categoria(nombre=entrada.nombre, peso=entrada.peso))
        else:
            actuales[entrada.id].nombre = entrada.nombre
            actuales[entrada.id].peso = entrada.peso

    sesion.commit()
    return materia.categorias


def _validar_lista(entradas: list[CategoriaEntrada]) -> None:
    suma = sum((entrada.peso for entrada in entradas), Decimal("0"))
    if suma != SUMA_REQUERIDA:
        raise ErrorApp(422, "PESOS_NO_SUMAN_100", f"Los pesos deben sumar 100; ahora suman {suma}")

    nombres = [entrada.nombre.strip().lower() for entrada in entradas]
    if len(set(nombres)) != len(nombres):
        raise ErrorApp(422, "NOMBRES_REPETIDOS", "Hay categorías con el mismo nombre")


def _categoria_tiene_calificaciones(sesion: Session, categoria_id: int) -> bool:
    consulta = select(Calificacion).join(Tarea).where(Tarea.categoria_id == categoria_id)
    return bool(sesion.scalar(select(exists(consulta))))


# --- Tareas ---


def crear_tarea(
    sesion: Session, nrc: str, categoria_id: int, usuario: UsuarioActual, nombre: str
) -> Tarea:
    materia = obtener_materia_con_acceso(sesion, nrc, usuario)
    categoria = _obtener_categoria(materia, categoria_id)
    _validar_nombre_de_tarea_libre(categoria, nombre)

    tarea = Tarea(nombre=nombre)
    categoria.tareas.append(tarea)
    sesion.commit()
    return tarea


def renombrar_tarea(
    sesion: Session, nrc: str, tarea_id: int, usuario: UsuarioActual, nombre: str
) -> Tarea:
    materia = obtener_materia_con_acceso(sesion, nrc, usuario)
    tarea = _obtener_tarea(sesion, materia, tarea_id)
    _validar_nombre_de_tarea_libre(tarea.categoria, nombre, excepto=tarea)

    tarea.nombre = nombre
    sesion.commit()
    return tarea


def eliminar_tarea(sesion: Session, nrc: str, tarea_id: int, usuario: UsuarioActual) -> None:
    materia = obtener_materia_con_acceso(sesion, nrc, usuario)
    tarea = _obtener_tarea(sesion, materia, tarea_id)
    if tarea.calificaciones:
        raise ErrorApp(
            409,
            "TAREA_CON_CALIFICACIONES",
            "No se puede eliminar una tarea que ya tiene calificaciones",
        )
    sesion.delete(tarea)
    sesion.commit()


def _obtener_categoria(materia: Materia, categoria_id: int) -> Categoria:
    for categoria in materia.categorias:
        if categoria.id == categoria_id:
            return categoria
    raise ErrorApp(404, "CATEGORIA_NO_ENCONTRADA", "La categoría no existe en esta materia")


def _obtener_tarea(sesion: Session, materia: Materia, tarea_id: int) -> Tarea:
    tarea = sesion.get(Tarea, tarea_id)
    # Una tarea de otra materia se trata como inexistente.
    if tarea is None or tarea.categoria.nrc != materia.nrc:
        raise ErrorApp(404, "TAREA_NO_ENCONTRADA", "La tarea no existe en esta materia")
    return tarea


def _validar_nombre_de_tarea_libre(
    categoria: Categoria, nombre: str, excepto: Tarea | None = None
) -> None:
    for tarea in categoria.tareas:
        if tarea is not excepto and tarea.nombre.strip().lower() == nombre.strip().lower():
            raise ErrorApp(
                409, "TAREA_DUPLICADA", f"Ya existe la tarea '{nombre}' en {categoria.nombre}"
            )
