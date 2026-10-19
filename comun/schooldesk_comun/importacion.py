"""Lectura y validación de archivos CSV para la importación masiva.

Flujo que sigue cada servicio:
    leer_csv  →  validar_filas  →  guardar (lógica propia del servicio)  →  ResultadoImportacion

Regla: todo o nada. Si alguna fila tiene errores no se guarda ninguna, y la
respuesta lista todos los errores con su número de fila para corregirlos de una vez.
"""

import csv
import io
from dataclasses import dataclass
from typing import TypeVar

from fastapi import Response
from pydantic import BaseModel, ValidationError

from schooldesk_comun.errores import ErrorApp

TAMANO_MAXIMO_BYTES = 1_000_000  # 1 MB
FILAS_MAXIMAS = 2000

Modelo = TypeVar("Modelo", bound=BaseModel)

# Pydantic genera mensajes en inglés; el admin los ve traducidos.
MENSAJES_VALIDACION = {
    "missing": "es obligatorio",
    "string_too_short": "no puede estar vacío",
    "string_too_long": "es demasiado largo",
    "string_pattern_mismatch": "tiene un formato inválido",
    "value_error": "tiene un valor inválido",
}


class ErrorFila(BaseModel):
    fila: int
    mensaje: str


class FilaOmitida(BaseModel):
    fila: int
    motivo: str


class ResultadoImportacion(BaseModel):
    creados: int
    omitidos: list[FilaOmitida]


@dataclass
class FilaCsv:
    numero: int  # número de fila como lo muestra Excel (la 1 es el encabezado)
    valores: dict[str, str]


def leer_csv(contenido: bytes, columnas: list[str]) -> list[FilaCsv]:
    """Convierte el archivo en filas con las columnas pedidas, ya sin espacios sobrantes."""
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise _archivo_invalido("El archivo pesa más de 1 MB")

    texto = _decodificar(contenido)
    if not texto.strip():
        raise _archivo_invalido("El archivo está vacío")

    lector = csv.DictReader(io.StringIO(texto), delimiter=_detectar_separador(texto))
    # "Matricula " y "matricula" se aceptan como la misma columna.
    lector.fieldnames = [(nombre or "").strip().lower() for nombre in lector.fieldnames or []]
    faltantes = [columna for columna in columnas if columna not in lector.fieldnames]
    if faltantes:
        raise _archivo_invalido(f"Faltan las columnas: {', '.join(faltantes)}")

    filas: list[FilaCsv] = []
    for valores in lector:
        limpios = {columna: (valores.get(columna) or "").strip() for columna in columnas}
        if any(limpios.values()):  # las filas totalmente vacías se ignoran
            filas.append(FilaCsv(numero=lector.line_num, valores=limpios))

    if not filas:
        raise _archivo_invalido("El archivo no tiene filas de datos")
    if len(filas) > FILAS_MAXIMAS:
        raise _archivo_invalido(f"El archivo tiene más de {FILAS_MAXIMAS} filas")
    return filas


def validar_filas(
    filas: list[FilaCsv], modelo: type[Modelo], campos_clave: tuple[str, ...]
) -> list[tuple[int, Modelo]]:
    """Valida cada fila con el modelo de Pydantic y detecta filas repetidas.

    `campos_clave` dice qué hace única a una fila: ("matricula",) para alumnos,
    ("nrc", "matricula") para inscripciones. Devuelve (número de fila, fila validada).
    """
    errores: list[ErrorFila] = []
    validas: list[tuple[int, Modelo]] = []
    primera_aparicion: dict[tuple[object, ...], int] = {}

    for fila in filas:
        try:
            objeto = modelo.model_validate(fila.valores)
        except ValidationError as error:
            errores.append(ErrorFila(fila=fila.numero, mensaje=_traducir(error)))
            continue

        clave = tuple(getattr(objeto, campo) for campo in campos_clave)
        if clave in primera_aparicion:
            mensaje = f"Fila repetida: ya aparece en la fila {primera_aparicion[clave]}"
            errores.append(ErrorFila(fila=fila.numero, mensaje=mensaje))
            continue

        primera_aparicion[clave] = fila.numero
        validas.append((fila.numero, objeto))

    if errores:
        raise error_de_filas(errores)
    return validas


def error_de_filas(errores: list[ErrorFila]) -> ErrorApp:
    """Error con la lista de filas inválidas. Los servicios también lo usan para
    errores que solo se detectan contra la base de datos (p. ej. email ya usado)."""
    return ErrorApp(
        422,
        "ARCHIVO_CON_ERRORES",
        f"{len(errores)} fila(s) con errores; no se guardó nada",
        extra={"filas": [error.model_dump() for error in errores]},
    )


def respuesta_plantilla(columnas: list[str], nombre_archivo: str) -> Response:
    """CSV vacío con los encabezados correctos, para que el admin lo llene en Excel.

    Lleva BOM al inicio para que Excel muestre bien los acentos.
    """
    contenido = "﻿" + ",".join(columnas) + "\n"
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


def _decodificar(contenido: bytes) -> str:
    # Excel guarda "CSV UTF-8" con BOM (utf-8-sig lo quita), pero el formato
    # "CSV (delimitado por comas)" lo guarda en cp1252, la codificación de Windows.
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    try:
        return contenido.decode("cp1252")
    except UnicodeDecodeError:
        raise _archivo_invalido("No se reconoce la codificación; guarda el archivo como CSV UTF-8")


def _detectar_separador(texto: str) -> str:
    # Excel usa ";" en algunas configuraciones regionales. Se decide por el encabezado.
    encabezado = texto.splitlines()[0]
    return ";" if encabezado.count(";") > encabezado.count(",") else ","


def _traducir(error: ValidationError) -> str:
    partes = []
    for detalle in error.errors():
        campo = detalle["loc"][0] if detalle["loc"] else "fila"
        partes.append(f"{campo} {MENSAJES_VALIDACION.get(detalle['type'], detalle['msg'])}")
    return "; ".join(partes)


def _archivo_invalido(detalle: str) -> ErrorApp:
    return ErrorApp(422, "ARCHIVO_INVALIDO", detalle)
