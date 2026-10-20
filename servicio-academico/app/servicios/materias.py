"""Materias, su docente titular y sus inscripciones."""

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.clientes.auth import ClienteAuth, Docente
from app.esquemas import MateriaEdicion, MateriaNueva
from app.modelos import Alumno, Calificacion, Categoria, Inscripcion, Materia, Tarea
from app.servicios.alumnos import obtener_alumno
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.roles import Rol
from schooldesk_comun.seguridad import UsuarioActual


def listar_materias(sesion: Session, usuario: UsuarioActual) -> list[Materia]:
    """El admin ve todas las materias; el docente, solo las que imparte."""
    consulta = select(Materia).order_by(Materia.nombre, Materia.seccion)
    if usuario.rol == Rol.DOCENTE:
        consulta = consulta.where(Materia.num_empleado_docente == usuario.usuario)
    return list(sesion.scalars(consulta))


def obtener_materia(sesion: Session, nrc: str) -> Materia:
    materia = sesion.get(Materia, nrc)
    if materia is None:
        raise ErrorApp(404, "MATERIA_NO_ENCONTRADA", f"No existe la materia con NRC {nrc}")
    return materia


def obtener_materia_con_acceso(sesion: Session, nrc: str, usuario: UsuarioActual) -> Materia:
    """La materia, si quien pregunta es el admin o el docente titular.

    La usan también ponderaciones y calificaciones: así la regla de quién puede
    ver o modificar una materia está escrita una sola vez.
    """
    materia = obtener_materia(sesion, nrc)
    if usuario.rol == Rol.ADMIN:
        return materia
    if usuario.rol == Rol.DOCENTE and materia.num_empleado_docente == usuario.usuario:
        return materia
    raise ErrorApp(403, "NO_ES_TU_MATERIA", "Solo el docente titular puede acceder a esta materia")


def crear_materia(sesion: Session, cliente_auth: ClienteAuth, datos: MateriaNueva) -> Materia:
    if sesion.get(Materia, datos.nrc) is not None:
        raise ErrorApp(409, "MATERIA_DUPLICADA", f"Ya existe la materia con NRC {datos.nrc}")
    docente = buscar_docente(cliente_auth, datos.num_empleado_docente)

    materia = Materia(
        nrc=datos.nrc,
        clave=datos.clave,
        nombre=datos.nombre,
        seccion=datos.seccion,
        num_empleado_docente=docente.usuario,
        nombre_docente=docente.nombre_completo,
    )
    sesion.add(materia)
    sesion.commit()
    return materia


def editar_materia(
    sesion: Session, cliente_auth: ClienteAuth, nrc: str, datos: MateriaEdicion
) -> Materia:
    materia = obtener_materia(sesion, nrc)

    if datos.clave is not None:
        materia.clave = datos.clave
    if datos.nombre is not None:
        materia.nombre = datos.nombre
    if datos.seccion is not None:
        materia.seccion = datos.seccion
    if datos.num_empleado_docente is not None:
        docente = buscar_docente(cliente_auth, datos.num_empleado_docente)
        materia.num_empleado_docente = docente.usuario
        materia.nombre_docente = docente.nombre_completo

    sesion.commit()
    return materia


def eliminar_materia(sesion: Session, nrc: str) -> None:
    materia = obtener_materia(sesion, nrc)
    if materia.inscripciones:
        raise ErrorApp(
            409, "MATERIA_CON_ALUMNOS", "No se puede eliminar una materia con alumnos inscritos"
        )
    sesion.delete(materia)  # sus categorías y tareas se borran en cascada
    sesion.commit()


def listar_inscritos(sesion: Session, nrc: str, usuario: UsuarioActual) -> list[Alumno]:
    obtener_materia_con_acceso(sesion, nrc, usuario)
    consulta = (
        select(Alumno)
        .join(Inscripcion)
        .where(Inscripcion.nrc == nrc)
        .order_by(Alumno.apellidos, Alumno.nombre)  # como las listas oficiales
    )
    return list(sesion.scalars(consulta))


def inscribir(sesion: Session, nrc: str, matricula: str) -> Alumno:
    obtener_materia(sesion, nrc)
    alumno = obtener_alumno(sesion, matricula)
    if sesion.get(Inscripcion, (nrc, matricula)) is not None:
        raise ErrorApp(
            409, "YA_INSCRITO", f"El alumno {matricula} ya está inscrito en la materia {nrc}"
        )

    sesion.add(Inscripcion(nrc=nrc, matricula=matricula))
    sesion.commit()
    return alumno


def dar_de_baja(sesion: Session, nrc: str, matricula: str) -> None:
    inscripcion = sesion.get(Inscripcion, (nrc, matricula))
    if inscripcion is None:
        raise ErrorApp(
            404, "NO_INSCRITO", f"El alumno {matricula} no está inscrito en la materia {nrc}"
        )
    if tiene_calificaciones(sesion, nrc, matricula):
        # Borrar la inscripción dejaría calificaciones huérfanas.
        raise ErrorApp(
            409,
            "ALUMNO_CON_CALIFICACIONES",
            "No se puede dar de baja a un alumno que ya tiene calificaciones",
        )
    sesion.delete(inscripcion)
    sesion.commit()


def tiene_calificaciones(sesion: Session, nrc: str, matricula: str) -> bool:
    consulta = (
        select(Calificacion)
        .join(Tarea)
        .join(Categoria)
        .where(Categoria.nrc == nrc, Calificacion.matricula == matricula)
    )
    return bool(sesion.scalar(select(exists(consulta))))


def buscar_docente(cliente_auth: ClienteAuth, num_empleado: str) -> Docente:
    """Valida contra auth que el docente exista y esté activo, y devuelve su nombre."""
    for docente in cliente_auth.listar_docentes():
        if docente.usuario == num_empleado:
            return docente
    raise ErrorApp(
        422,
        "DOCENTE_NO_ENCONTRADO",
        f"No hay un docente activo con número de empleado {num_empleado}",
    )
