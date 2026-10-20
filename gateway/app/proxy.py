"""Reenvío de peticiones: /api/{servicio}/{ruta} → {url del servicio}/{ruta}.

El gateway no tiene lógica de negocio ni valida el JWT: solo enruta. Cada
servicio valida el token por su cuenta, así que aunque alguien llamara a un
servicio sin pasar por aquí, seguiría protegido.
"""

import httpx
from fastapi import Request, Response

from schooldesk_comun.errores import ErrorApp

# Encabezados que no se copian al reenviar la petición:
# - los de la conexión (host, content-length...) los pone httpx para la nueva petición;
# - X-Clave-Interna se quita para que nadie de fuera pueda hacerse pasar por un servicio.
NO_REENVIAR_EN_PETICION = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "transfer-encoding",
    "x-clave-interna",
}

# httpx ya descomprimió y armó el cuerpo, así que estos ya no describen lo que se devuelve.
NO_REENVIAR_EN_RESPUESTA = {"content-length", "content-encoding", "transfer-encoding", "connection"}


def es_ruta_interna(ruta: str) -> bool:
    return ruta == "interno" or ruta.startswith("interno/")


async def reenviar(
    cliente: httpx.AsyncClient, servicio: str, url_base: str, ruta: str, peticion: Request
) -> Response:
    if es_ruta_interna(ruta):
        # 404 y no 403: desde fuera, las rutas internas simplemente no existen.
        raise ErrorApp(404, "RUTA_NO_ENCONTRADA", "La ruta no existe")

    encabezados = {
        nombre: valor
        for nombre, valor in peticion.headers.items()
        if nombre.lower() not in NO_REENVIAR_EN_PETICION
    }
    try:
        respuesta = await cliente.request(
            peticion.method,
            f"{url_base}/{ruta}",
            params=list(peticion.query_params.multi_items()),
            headers=encabezados,
            content=await peticion.body(),
        )
    except httpx.TimeoutException:  # va antes porque también es un HTTPError
        raise ErrorApp(504, "TIEMPO_AGOTADO", f"El servicio {servicio} tardó demasiado en responder")
    except httpx.HTTPError:
        raise ErrorApp(503, "SERVICIO_NO_DISPONIBLE", f"El servicio {servicio} no está disponible")

    return Response(
        content=respuesta.content,
        status_code=respuesta.status_code,
        headers={
            nombre: valor
            for nombre, valor in respuesta.headers.items()
            if nombre.lower() not in NO_REENVIAR_EN_RESPUESTA
        },
    )
