"""Captura de calificaciones y concentrado de la materia (admin o docente titular)."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculo import CategoriaParaCalculo, calcular_promedios
from app.esquemas import CalificacionEntrada, CategoriaRespuesta, Concentrado, FilaConcentrado
from app.modelos import Calificacion, Categoria, Materia, Tarea
from app.servicios.materias import listar_inscritos, obtener_materia_con_acceso
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.seguridad import UsuarioActual


def obtener_concentrado(sesion: Session, nrc: str, usuario: UsuarioActual) -> Concentrado:
    materia = obtener_materia_con_acceso(sesion, nrc, usuario)
    alumnos = listar_inscritos(sesion, nrc, usuario)
    puntos = puntos_de_la_materia(sesion, nrc)
    categorias = categorias_para_calculo(materia)

    filas = []
    for alumno in alumnos:
        puntos_del_alumno = puntos.get(alumno.matricula, {})
        promedios = calcular_promedios(categorias, puntos_del_alumno)
        filas.append(
            FilaConcentrado(
                matricula=alumno.matricula,
                nombre=alumno.nombre,
                apellidos=alumno.apellidos,
                # Todas las tareas aparecen; las que no tienen calificación, como null.
                puntos={
                    tarea_id: puntos_del_alumno.get(tarea_id)
                    for categoria in categorias
                    for tarea_id in categoria.tarea_ids
                },
                promedios_categoria=promedios.por_categoria,
                promedio=promedios.final,
            )
        )

    return Concentrado(
        categorias=[CategoriaRespuesta.model_validate(c) for c in materia.categorias],
        alumnos=filas,
    )


def capturar_calificaciones(
    sesion: Session, nrc: str, usuario: UsuarioActual, entradas: list[CalificacionEntrada]
) -> Concentrado:
    """Guarda varias calificaciones a la vez (todas o ninguna) y devuelve el concentrado."""
    materia = obtener_materia_con_acceso(sesion, nrc, usuario)
    _validar_entradas(sesion, materia, usuario, entradas)

    existentes = {
        (calificacion.matricula, calificacion.tarea_id): calificacion
        for calificacion in _calificaciones_de_la_materia(sesion, nrc)
    }
    for entrada in entradas:
        actual = existentes.get((entrada.matricula, entrada.tarea_id))
        if entrada.puntos is None:
            if actual is not None:
                sesion.delete(actual)  # vuelve a "sin calificar"
        elif actual is None:
            sesion.add(
                Calificacion(
                    tarea_id=entrada.tarea_id, matricula=entrada.matricula, puntos=entrada.puntos
                )
            )
        else:
            actual.puntos = entrada.puntos

    sesion.commit()
    return obtener_concentrado(sesion, nrc, usuario)


# --- Funciones que también usa la vista del alumno ---


def puntos_de_la_materia(sesion: Session, nrc: str) -> dict[str, dict[int, Decimal]]:
    """{matrícula: {tarea_id: puntos}} con todas las calificaciones de la materia.

    Una sola consulta para toda la materia, en vez de una por alumno (el
    problema "N+1": con 30 alumnos serían 31 consultas).
    """
    puntos: dict[str, dict[int, Decimal]] = {}
    for calificacion in _calificaciones_de_la_materia(sesion, nrc):
        puntos.setdefault(calificacion.matricula, {})[calificacion.tarea_id] = calificacion.puntos
    return puntos


def categorias_para_calculo(materia: Materia) -> list[CategoriaParaCalculo]:
    return [
        CategoriaParaCalculo(
            id=categoria.id,
            peso=categoria.peso,
            tarea_ids=[tarea.id for tarea in categoria.tareas],
        )
        for categoria in materia.categorias
    ]


def puntos_del_alumno_por_materia(sesion: Session, matricula: str) -> dict[str, dict[int, Decimal]]:
    """{nrc: {tarea_id: puntos}} de UN alumno en todas sus materias, en una sola consulta."""
    consulta = (
        select(Categoria.nrc, Calificacion.tarea_id, Calificacion.puntos)
        .select_from(Calificacion)
        .join(Tarea)
        .join(Categoria)
        .where(Calificacion.matricula == matricula)
    )
    puntos: dict[str, dict[int, Decimal]] = {}
    for nrc, tarea_id, valor in sesion.execute(consulta):
        puntos.setdefault(nrc, {})[tarea_id] = valor
    return puntos


# --- Privadas ---


def _calificaciones_de_la_materia(sesion: Session, nrc: str) -> list[Calificacion]:
    consulta = select(Calificacion).join(Tarea).join(Categoria).where(Categoria.nrc == nrc)
    return list(sesion.scalars(consulta))


def _validar_entradas(
    sesion: Session, materia: Materia, usuario: UsuarioActual, entradas: list[CalificacionEntrada]
) -> None:
    """Revisa TODAS las entradas y reporta todos los problemas juntos.

    El frontend solo muestra alumnos inscritos y tareas de la materia, pero el
    backend no confía en el frontend: la petición podría venir de otro lado.
    """
    inscritos = {alumno.matricula for alumno in listar_inscritos(sesion, materia.nrc, usuario)}
    tareas = {tarea.id for categoria in materia.categorias for tarea in categoria.tareas}

    errores: list[str] = []
    vistas: set[tuple[str, int]] = set()
    for entrada in entradas:
        if entrada.matricula not in inscritos:
            errores.append(f"El alumno {entrada.matricula} no está inscrito en la materia")
        if entrada.tarea_id not in tareas:
            errores.append(f"La tarea {entrada.tarea_id} no es de esta materia")
        if (entrada.matricula, entrada.tarea_id) in vistas:
            errores.append(
                f"La calificación de {entrada.matricula} "
                f"en la tarea {entrada.tarea_id} viene repetida"
            )
        vistas.add((entrada.matricula, entrada.tarea_id))

    if errores:
        raise ErrorApp(
            422,
            "CALIFICACIONES_INVALIDAS",
            f"{len(errores)} problema(s); no se guardó nada",
            extra={"errores": errores},
        )
