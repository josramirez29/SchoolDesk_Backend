"""Funciones para crear datos de prueba sin repetir código en cada archivo.

Usan los mismos datos de datos-ejemplo/ para que las pruebas se parezcan a la demo.
"""

from typing import Any

from app.modelos import Alumno, Materia


def nuevo_alumno(**cambios: Any) -> Alumno:
    datos: dict[str, Any] = {
        "matricula": "202231045",
        "nombre": "Ana Sofía",
        "apellidos": "Acosta Bravo",
    }
    datos.update(cambios)
    return Alumno(**datos)


def nueva_materia(**cambios: Any) -> Materia:
    datos: dict[str, Any] = {
        "nrc": "48308",
        "clave": "ITIS 702",
        "nombre": "Desarrollo de Sitios Web",
        "seccion": "001",
        "num_empleado_docente": "100521347",
        "nombre_docente": "Laura Méndez Ortega",
    }
    datos.update(cambios)
    return Materia(**datos)
