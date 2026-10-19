"""Importación masiva de docentes desde CSV."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contrasenas import generar_hashes
from app.esquemas import COLUMNAS_DOCENTES, FilaDocente
from app.modelos import Usuario
from schooldesk_comun.importacion import (
    ErrorFila,
    FilaOmitida,
    ResultadoImportacion,
    error_de_filas,
    leer_csv,
    validar_filas,
)
from schooldesk_comun.roles import Rol


def importar_docentes(sesion: Session, contenido: bytes) -> ResultadoImportacion:
    filas = validar_filas(
        leer_csv(contenido, COLUMNAS_DOCENTES), FilaDocente, campos_clave=("num_empleado",)
    )

    # Idempotente: si el docente ya existe se omite, así subir el mismo archivo
    # dos veces no truena ni duplica nada.
    ya_existen = set(
        sesion.scalars(
            select(Usuario.usuario).where(Usuario.usuario.in_([f.num_empleado for _, f in filas]))
        )
    )
    nuevas = [(numero, fila) for numero, fila in filas if fila.num_empleado not in ya_existen]
    omitidos = [
        FilaOmitida(fila=numero, motivo="Ya existe una cuenta con ese número de empleado")
        for numero, fila in filas
        if fila.num_empleado in ya_existen
    ]

    errores = _errores_de_email(sesion, nuevas)
    if errores:
        raise error_de_filas(errores)

    # Contraseña inicial = número de empleado (igual que en el alta manual).
    hashes = generar_hashes([fila.num_empleado for _, fila in nuevas])
    sesion.add_all(
        Usuario(
            usuario=fila.num_empleado,
            nombre=fila.nombre,
            apellidos=fila.apellidos,
            email=fila.email,
            hash_contrasena=hash_contrasena,
            rol=Rol.DOCENTE,
        )
        for (_, fila), hash_contrasena in zip(nuevas, hashes)
    )
    sesion.commit()  # una sola transacción: se guardan todos o ninguno

    return ResultadoImportacion(creados=len(nuevas), omitidos=omitidos)


def _errores_de_email(sesion: Session, nuevas: list[tuple[int, FilaDocente]]) -> list[ErrorFila]:
    """El email es único: no puede repetirse en el archivo ni ser de otra cuenta."""
    emails = [fila.email for _, fila in nuevas]
    en_base = set(sesion.scalars(select(Usuario.email).where(Usuario.email.in_(emails))))

    errores: list[ErrorFila] = []
    primera_aparicion: dict[str, int] = {}
    for numero, fila in nuevas:
        if fila.email in en_base:
            mensaje = f"El correo {fila.email} ya pertenece a otra cuenta"
            errores.append(ErrorFila(fila=numero, mensaje=mensaje))
        elif fila.email in primera_aparicion:
            mensaje = f"El correo {fila.email} ya aparece en la fila {primera_aparicion[fila.email]}"
            errores.append(ErrorFila(fila=numero, mensaje=mensaje))
        else:
            primera_aparicion[fila.email] = numero
    return errores
