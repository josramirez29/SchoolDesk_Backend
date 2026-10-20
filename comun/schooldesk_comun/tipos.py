"""Tipos de datos que deben validarse igual en todos los servicios.

Igual que los roles: si el formato de la matrícula cambiara, se cambia solo aquí.
"""

from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field

# Matrícula de alumno o número de empleado: 9 dígitos, formato BUAP.
Identificador = Annotated[str, Field(pattern=r"^\d{9}$", examples=["202231045"])]

# NRC de una materia: 5 dígitos.
Nrc = Annotated[str, Field(pattern=r"^\d{5}$", examples=["48308"])]

# "Laura.Mendez@..." y "laura.mendez@..." son el mismo correo: se guarda en minúsculas.
EmailNormalizado = Annotated[EmailStr, AfterValidator(str.lower)]
