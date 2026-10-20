"""Alta, búsqueda y edición de alumnos (solo el admin llega aquí)."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.clientes.auth import ClienteAuth, CuentaAlumno
from app.esquemas import AlumnoDetalle, AlumnoEdicion, AlumnoNuevo, MateriaResumen
from app.modelos import Alumno
from schooldesk_comun.errores import ErrorApp


def buscar_alumnos(sesion: Session, buscar: str | None = None) -> list[Alumno]:
    consulta = select(Alumno).order_by(Alumno.apellidos, Alumno.nombre)
    if buscar:
        patron = f"%{buscar.strip()}%"
        # Busca por matrícula o por nombre completo, sin importar mayúsculas.
        consulta = consulta.where(
            or_(
                Alumno.matricula.like(patron),
                (Alumno.nombre + " " + Alumno.apellidos).ilike(patron),
            )
        )
    return list(sesion.scalars(consulta))


def obtener_alumno(sesion: Session, matricula: str) -> Alumno:
    alumno = sesion.get(Alumno, matricula)
    if alumno is None:
        raise ErrorApp(
            404, "ALUMNO_NO_ENCONTRADO", f"No existe el alumno con matrícula {matricula}"
        )
    return alumno


def obtener_detalle(sesion: Session, matricula: str) -> AlumnoDetalle:
    alumno = obtener_alumno(sesion, matricula)
    materias = sorted(
        (inscripcion.materia for inscripcion in alumno.inscripciones),
        key=lambda materia: materia.nombre,
    )
    return AlumnoDetalle(
        matricula=alumno.matricula,
        nombre=alumno.nombre,
        apellidos=alumno.apellidos,
        materias=[MateriaResumen.model_validate(materia) for materia in materias],
    )


def crear_alumno(sesion: Session, cliente_auth: ClienteAuth, datos: AlumnoNuevo) -> Alumno:
    if sesion.get(Alumno, datos.matricula) is not None:
        raise ErrorApp(
            409, "ALUMNO_DUPLICADO", f"Ya existe el alumno con matrícula {datos.matricula}"
        )

    # 1) Primero la cuenta en auth. Si auth falla, aquí no se guardó nada.
    # 2) Después el registro académico. Si esto fallara, repetir el alta es
    #    seguro: auth omite la cuenta que ya existe (es idempotente).
    cuenta = CuentaAlumno(
        usuario=datos.matricula, nombre=datos.nombre, apellidos=datos.apellidos, email=datos.email
    )
    cliente_auth.crear_cuentas_alumnos([cuenta])

    alumno = Alumno(matricula=datos.matricula, nombre=datos.nombre, apellidos=datos.apellidos)
    sesion.add(alumno)
    sesion.commit()
    return alumno


def editar_alumno(
    sesion: Session, cliente_auth: ClienteAuth, matricula: str, datos: AlumnoEdicion
) -> Alumno:
    alumno = obtener_alumno(sesion, matricula)
    nombre = datos.nombre if datos.nombre is not None else alumno.nombre
    apellidos = datos.apellidos if datos.apellidos is not None else alumno.apellidos

    # Mismo orden que al crear: primero auth, después la base local.
    cliente_auth.actualizar_nombre(matricula, nombre, apellidos)
    alumno.nombre = nombre
    alumno.apellidos = apellidos
    sesion.commit()
    return alumno
