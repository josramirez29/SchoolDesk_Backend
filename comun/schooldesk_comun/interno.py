import secrets

from fastapi import Header

from schooldesk_comun.configuracion import obtener_configuracion_comun
from schooldesk_comun.errores import ErrorApp


def requerir_clave_interna(x_clave_interna: str | None = Header(default=None)) -> None:
    """Protege los endpoints /interno/..., que solo llaman otros servicios.

    FastAPI lee el header "X-Clave-Interna". Se usa compare_digest para que
    la comparación tarde lo mismo sin importar en qué carácter falle
    (evita ataques de tiempo).
    """
    esperada = obtener_configuracion_comun().clave_interna
    if not secrets.compare_digest(x_clave_interna or "", esperada):
        raise ErrorApp(401, "CLAVE_INTERNA_INVALIDA", "Llamada interna no autorizada")
