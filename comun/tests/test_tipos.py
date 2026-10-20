import pytest
from pydantic import BaseModel, ValidationError

from schooldesk_comun.tipos import EmailNormalizado, Identificador, Nrc


class Ejemplo(BaseModel):
    identificador: Identificador
    nrc: Nrc
    email: EmailNormalizado


def test_valores_validos_y_email_en_minusculas() -> None:
    ejemplo = Ejemplo(identificador="202231045", nrc="48308", email="Ana.Acosta@Alumno.Example.com")

    assert ejemplo.email == "ana.acosta@alumno.example.com"


@pytest.mark.parametrize("identificador", ["20223104", "2022310450", "20223104a"])
def test_identificador_debe_tener_exactamente_9_digitos(identificador: str) -> None:
    with pytest.raises(ValidationError):
        Ejemplo(identificador=identificador, nrc="48308", email="a@example.com")


def test_nrc_debe_tener_5_digitos() -> None:
    with pytest.raises(ValidationError):
        Ejemplo(identificador="202231045", nrc="4830", email="a@example.com")
