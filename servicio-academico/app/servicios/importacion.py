"""Importación masiva de alumnos, materias e inscripciones desde CSV.

Las tres siguen el mismo flujo (igual que la de docentes en auth):
    1. leer y validar todas las filas (formato y repetidos dentro del archivo)
    2. separar las que ya existen → se omiten (importar dos veces es seguro)
    3. validar contra la base y contra auth → si algo falla, no se guarda nada
    4. guardar todo en una sola transacción
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clientes.auth import ClienteAuth, CuentaAlumno
from app.esquemas import (
    COLUMNAS_ALUMNOS,
    COLUMNAS_INSCRIPCIONES,
    COLUMNAS_MATERIAS,
    AlumnoNuevo,
    FilaInscripcion,
    MateriaNueva,
)
from app.modelos import Alumno, Inscripcion, Materia
from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.importacion import (
    ErrorFila,
    FilaOmitida,
    ResultadoImportacion,
    error_de_filas,
    leer_csv,
    validar_filas,
)

# --- Alumnos ---


def importar_alumnos(
    sesion: Session, cliente_auth: ClienteAuth, contenido: bytes
) -> ResultadoImportacion:
    filas = validar_filas(
        leer_csv(contenido, COLUMNAS_ALUMNOS), AlumnoNuevo, campos_clave=("matricula",)
    )
    errores = _emails_repetidos_en_el_archivo(filas)
    if errores:
        raise error_de_filas(errores)

    ya_existen = set(
        sesion.scalars(
            select(Alumno.matricula).where(Alumno.matricula.in_([f.matricula for _, f in filas]))
        )
    )
    nuevas = [(numero, fila) for numero, fila in filas if fila.matricula not in ya_existen]
    omitidos = [
        FilaOmitida(fila=numero, motivo="Ya existe el alumno con esa matrícula")
        for numero, fila in filas
        if fila.matricula in ya_existen
    ]
    if not nuevas:
        return ResultadoImportacion(creados=0, omitidos=omitidos)

    # Todas las cuentas en UNA llamada a auth (no una por alumno).
    cuentas = [
        CuentaAlumno(
            usuario=fila.matricula, nombre=fila.nombre, apellidos=fila.apellidos, email=fila.email
        )
        for _, fila in nuevas
    ]
    try:
        cliente_auth.crear_cuentas_alumnos(cuentas)
    except ErrorApp as error:
        # auth no conoce las filas del archivo; aquí se traduce su error a filas.
        errores = _filas_en_conflicto_con_auth(error, nuevas)
        if errores:
            raise error_de_filas(errores)
        raise

    sesion.add_all(
        Alumno(matricula=fila.matricula, nombre=fila.nombre, apellidos=fila.apellidos)
        for _, fila in nuevas
    )
    sesion.commit()
    return ResultadoImportacion(creados=len(nuevas), omitidos=omitidos)


def _emails_repetidos_en_el_archivo(filas: list[tuple[int, AlumnoNuevo]]) -> list[ErrorFila]:
    errores: list[ErrorFila] = []
    primera_aparicion: dict[str, int] = {}
    for numero, fila in filas:
        if fila.email in primera_aparicion:
            mensaje = f"El correo {fila.email} ya aparece en la fila {primera_aparicion[fila.email]}"
            errores.append(ErrorFila(fila=numero, mensaje=mensaje))
        else:
            primera_aparicion[fila.email] = numero
    return errores


def _filas_en_conflicto_con_auth(
    error: ErrorApp, filas: list[tuple[int, AlumnoNuevo]]
) -> list[ErrorFila]:
    if error.error == "EMAIL_EN_USO":
        emails = set(error.extra.get("emails", []))
        return [
            ErrorFila(fila=numero, mensaje=f"El correo {fila.email} ya pertenece a otra cuenta")
            for numero, fila in filas
            if fila.email in emails
        ]
    if error.error == "USUARIO_CON_OTRO_ROL":
        usuarios = set(error.extra.get("usuarios", []))
        return [
            ErrorFila(
                fila=numero,
                mensaje=f"La matrícula {fila.matricula} ya es de una cuenta que no es de alumno",
            )
            for numero, fila in filas
            if fila.matricula in usuarios
        ]
    return []


# --- Materias ---


def importar_materias(
    sesion: Session, cliente_auth: ClienteAuth, contenido: bytes
) -> ResultadoImportacion:
    filas = validar_filas(
        leer_csv(contenido, COLUMNAS_MATERIAS), MateriaNueva, campos_clave=("nrc",)
    )

    ya_existen = set(
        sesion.scalars(select(Materia.nrc).where(Materia.nrc.in_([f.nrc for _, f in filas])))
    )
    nuevas = [(numero, fila) for numero, fila in filas if fila.nrc not in ya_existen]
    omitidos = [
        FilaOmitida(fila=numero, motivo="Ya existe la materia con ese NRC")
        for numero, fila in filas
        if fila.nrc in ya_existen
    ]
    if not nuevas:
        return ResultadoImportacion(creados=0, omitidos=omitidos)

    # Una sola llamada a auth para validar a todos los docentes del archivo.
    docentes = {docente.usuario: docente for docente in cliente_auth.listar_docentes()}
    errores = [
        ErrorFila(
            fila=numero,
            mensaje=f"No hay un docente activo con número de empleado {fila.num_empleado_docente}",
        )
        for numero, fila in nuevas
        if fila.num_empleado_docente not in docentes
    ]
    if errores:
        raise error_de_filas(errores)

    sesion.add_all(
        Materia(
            nrc=fila.nrc,
            clave=fila.clave,
            nombre=fila.nombre,
            seccion=fila.seccion,
            num_empleado_docente=fila.num_empleado_docente,
            nombre_docente=docentes[fila.num_empleado_docente].nombre_completo,
        )
        for _, fila in nuevas
    )
    sesion.commit()
    return ResultadoImportacion(creados=len(nuevas), omitidos=omitidos)


# --- Inscripciones ---


def importar_inscripciones(sesion: Session, contenido: bytes) -> ResultadoImportacion:
    filas = validar_filas(
        leer_csv(contenido, COLUMNAS_INSCRIPCIONES),
        FilaInscripcion,
        campos_clave=("nrc", "matricula"),
    )

    nrcs = {fila.nrc for _, fila in filas}
    matriculas = {fila.matricula for _, fila in filas}
    materias = set(sesion.scalars(select(Materia.nrc).where(Materia.nrc.in_(nrcs))))
    alumnos = set(sesion.scalars(select(Alumno.matricula).where(Alumno.matricula.in_(matriculas))))

    errores: list[ErrorFila] = []
    for numero, fila in filas:
        if fila.nrc not in materias:
            errores.append(ErrorFila(fila=numero, mensaje=f"No existe la materia con NRC {fila.nrc}"))
        if fila.matricula not in alumnos:
            mensaje = f"No existe el alumno con matrícula {fila.matricula}"
            errores.append(ErrorFila(fila=numero, mensaje=mensaje))
    if errores:
        raise error_de_filas(errores)

    consulta = select(Inscripcion.nrc, Inscripcion.matricula).where(Inscripcion.nrc.in_(nrcs))
    ya_inscritos = {(nrc, matricula) for nrc, matricula in sesion.execute(consulta)}
    nuevas = [fila for _, fila in filas if (fila.nrc, fila.matricula) not in ya_inscritos]
    omitidos = [
        FilaOmitida(fila=numero, motivo="El alumno ya está inscrito en esa materia")
        for numero, fila in filas
        if (fila.nrc, fila.matricula) in ya_inscritos
    ]

    sesion.add_all(Inscripcion(nrc=fila.nrc, matricula=fila.matricula) for fila in nuevas)
    sesion.commit()
    return ResultadoImportacion(creados=len(nuevas), omitidos=omitidos)
