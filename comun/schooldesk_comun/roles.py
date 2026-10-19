from enum import StrEnum


class Rol(StrEnum):
    """Única definición de roles del sistema.

    Los valores son los que viajan en el JWT; ningún servicio debe
    escribirlos a mano como texto.
    """

    ADMIN = "ADMIN"
    DOCENTE = "DOCENTE"
    ALUMNO = "ALUMNO"
