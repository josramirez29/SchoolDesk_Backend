"""Lo que ve el alumno: sus materias y sus calificaciones.

La matrícula sale del token, nunca de la URL: así un alumno no puede pedir
las calificaciones de otro cambiando un número en la ruta.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculo import calcular_promedios
from app.esquemas import MateriaResumen, MiCategoria, MiMateria, MisCalificaciones, MiTarea
from app.modelos import Inscripcion, Materia
from app.servicios.calificaciones import categorias_para_calculo, puntos_del_alumno_por_materia
from schooldesk_comun.errores import ErrorApp


def listar_mis_materias(sesion: Session, matricula: str) -> list[MiMateria]:
    consulta = (
        select(Materia)
        .join(Inscripcion)
        .where(Inscripcion.matricula == matricula)
        .order_by(Materia.nombre)
    )
    materias = list(sesion.scalars(consulta))
    puntos = puntos_del_alumno_por_materia(sesion, matricula)  # una consulta para todas

    resultado = []
    for materia in materias:
        promedios = calcular_promedios(
            categorias_para_calculo(materia), puntos.get(materia.nrc, {})
        )
        resultado.append(
            MiMateria(
                **MateriaResumen.model_validate(materia).model_dump(),
                promedio=promedios.final,
            )
        )
    return resultado


def obtener_mis_calificaciones(sesion: Session, matricula: str, nrc: str) -> MisCalificaciones:
    if sesion.get(Inscripcion, (nrc, matricula)) is None:
        # 404 y no 403: al alumno no le decimos si la materia existe o no.
        raise ErrorApp(404, "NO_INSCRITO", "No estás inscrito en esta materia")

    materia = sesion.get(Materia, nrc)
    puntos = puntos_del_alumno_por_materia(sesion, matricula).get(nrc, {})
    promedios = calcular_promedios(categorias_para_calculo(materia), puntos)

    return MisCalificaciones(
        materia=MateriaResumen.model_validate(materia),
        promedio=promedios.final,
        categorias=[
            MiCategoria(
                id=categoria.id,
                nombre=categoria.nombre,
                peso=categoria.peso,
                promedio=promedios.por_categoria[categoria.id],
                tareas=[
                    MiTarea(id=tarea.id, nombre=tarea.nombre, puntos=puntos.get(tarea.id))
                    for tarea in categoria.tareas
                ],
            )
            for categoria in materia.categorias
        ],
    )
