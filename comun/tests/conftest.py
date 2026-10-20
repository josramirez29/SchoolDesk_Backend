from collections.abc import Iterator

import pytest

from schooldesk_comun.configuracion import obtener_configuracion_comun

CLAVE_JWT_PRUEBA = "clave-jwt-de-prueba-con-al-menos-32-bytes"
CLAVE_INTERNA_PRUEBA = "clave-interna-de-prueba-de-32-bytes"


@pytest.fixture(autouse=True)
def entorno_comun(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("CLAVE_JWT", CLAVE_JWT_PRUEBA)
    monkeypatch.setenv("CLAVE_INTERNA", CLAVE_INTERNA_PRUEBA)
    obtener_configuracion_comun.cache_clear()
    yield
    obtener_configuracion_comun.cache_clear()
