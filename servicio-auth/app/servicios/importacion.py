"""Importación masiva de docentes desde CSV."""

from sqlalchemy.orm import Session

from app.esquemas import COLUMNAS_DOCENTES, CuentaNueva, FilaDocente
from app.servicios.usuarios import emails_en_uso, guardar_cuentas_nuevas, usuarios_existentes
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
    ya_existen = usuarios_existentes(sesion, [fila.num_empleado for _, fila in filas])
    nuevas = [(numero, fila) for numero, fila in filas if fila.num_empleado not in ya_existen]
    omitidos = [
        FilaOmitida(fila=numero, motivo="Ya existe una cuenta con ese número de empleado")
        for numero, fila in filas
        if fila.num_empleado in ya_existen
    ]

    errores = _errores_de_email(sesion, nuevas)
    if errores:
        raise error_de_filas(errores)

    cuentas = [
        CuentaNueva(
            usuario=fila.num_empleado, nombre=fila.nombre, apellidos=fila.apellidos, email=fila.email
        )
        for _, fila in nuevas
    ]
    guardar_cuentas_nuevas(sesion, cuentas, Rol.DOCENTE)
    return ResultadoImportacion(creados=len(cuentas), omitidos=omitidos)


def _errores_de_email(sesion: Session, nuevas: list[tuple[int, FilaDocente]]) -> list[ErrorFila]:
    """El email es único: no puede repetirse en el archivo ni ser de otra cuenta."""
    en_base = emails_en_uso(sesion, [fila.email for _, fila in nuevas])

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
