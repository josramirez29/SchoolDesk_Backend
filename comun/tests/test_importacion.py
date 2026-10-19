import pytest
from pydantic import BaseModel, EmailStr, Field

from schooldesk_comun.errores import ErrorApp
from schooldesk_comun.importacion import leer_csv, validar_filas

COLUMNAS = ["matricula", "nombre", "email"]


class FilaPrueba(BaseModel):
    matricula: str = Field(pattern=r"^\d{9}$")
    nombre: str = Field(min_length=1)
    email: EmailStr


def test_lee_utf8_con_bom_y_conserva_acentos() -> None:
    contenido = "﻿matricula,nombre,email\n202231045,Ana Sofía,ana@example.com\n".encode()

    filas = leer_csv(contenido, COLUMNAS)

    assert filas[0].valores == {"matricula": "202231045", "nombre": "Ana Sofía", "email": "ana@example.com"}


def test_lee_el_formato_csv_de_excel_en_windows() -> None:
    # "CSV (delimitado por comas)" de Excel se guarda en cp1252, no en UTF-8.
    contenido = "matricula,nombre,email\n202231045,Begoña,bego@example.com\n".encode("cp1252")

    filas = leer_csv(contenido, COLUMNAS)

    assert filas[0].valores["nombre"] == "Begoña"


def test_acepta_punto_y_coma_como_separador() -> None:
    contenido = b"matricula;nombre;email\n202231045;Ana;ana@example.com\n"

    filas = leer_csv(contenido, COLUMNAS)

    assert filas[0].valores["nombre"] == "Ana"


def test_numera_las_filas_como_excel_e_ignora_filas_vacias() -> None:
    contenido = b"matricula,nombre,email\n202231045,Ana,a@example.com\n,,\n202233918,Bruno,b@example.com\n"

    filas = leer_csv(contenido, COLUMNAS)

    assert [fila.numero for fila in filas] == [2, 4]


def test_encabezados_con_mayusculas_y_espacios_se_aceptan() -> None:
    contenido = b" Matricula ,NOMBRE,Email\n202231045,Ana,a@example.com\n"

    assert len(leer_csv(contenido, COLUMNAS)) == 1


def test_columnas_faltantes_se_reportan() -> None:
    with pytest.raises(ErrorApp) as error:
        leer_csv(b"matricula,nombre\n202231045,Ana\n", COLUMNAS)

    assert error.value.error == "ARCHIVO_INVALIDO"
    assert "email" in error.value.detalle


def test_archivo_sin_datos_se_rechaza() -> None:
    with pytest.raises(ErrorApp):
        leer_csv(b"matricula,nombre,email\n", COLUMNAS)


def test_validar_reporta_todas_las_filas_con_error_y_no_devuelve_nada() -> None:
    contenido = (
        "matricula,nombre,email\n"
        "202231045,Ana,ana@example.com\n"
        "20223,Bruno,bruno@example.com\n"  # matrícula corta
        "202235502,,camila@example.com\n"  # nombre vacío
        "202231045,Ana otra vez,otra@example.com\n"  # matrícula repetida
    ).encode()
    filas = leer_csv(contenido, COLUMNAS)

    with pytest.raises(ErrorApp) as error:
        validar_filas(filas, FilaPrueba, campos_clave=("matricula",))

    assert error.value.error == "ARCHIVO_CON_ERRORES"
    assert error.value.extra["filas"] == [
        {"fila": 3, "mensaje": "matricula tiene un formato inválido"},
        {"fila": 4, "mensaje": "nombre no puede estar vacío"},
        {"fila": 5, "mensaje": "Fila repetida: ya aparece en la fila 2"},
    ]


def test_validar_devuelve_las_filas_validadas_con_su_numero() -> None:
    filas = leer_csv(b"matricula,nombre,email\n202231045,Ana,ana@example.com\n", COLUMNAS)

    validas = validar_filas(filas, FilaPrueba, campos_clave=("matricula",))

    numero, fila = validas[0]
    assert numero == 2
    assert fila.matricula == "202231045"
