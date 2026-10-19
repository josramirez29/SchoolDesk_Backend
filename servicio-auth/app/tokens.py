from datetime import UTC, datetime, timedelta

import jwt

from app.configuracion import obtener_configuracion
from app.modelos import Usuario
from schooldesk_comun.configuracion import obtener_configuracion_comun
from schooldesk_comun.seguridad import ALGORITMO_JWT


def crear_token(usuario: Usuario) -> str:
    """Firma un JWT con lo que los demás servicios necesitan saber del usuario.

    Lleva el identificador estable (sub), el nombre y el rol, así que ningún
    servicio tiene que preguntarle a auth quién es el usuario.
    """
    ahora = datetime.now(UTC)
    minutos = obtener_configuracion().minutos_expiracion_token
    datos = {
        "sub": usuario.usuario,
        "nombre": usuario.nombre_completo,
        "rol": usuario.rol.value,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=minutos),
    }
    return jwt.encode(datos, obtener_configuracion_comun().clave_jwt, algorithm=ALGORITMO_JWT)
