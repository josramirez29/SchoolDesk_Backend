import pytest
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.modelos import Usuario
from schooldesk_comun.roles import Rol
from tests.fabricas import nuevo_usuario


def test_usuario_se_guarda_con_valores_por_defecto(sesion: Session) -> None:
    sesion.add(nuevo_usuario())
    sesion.commit()

    guardado = sesion.get(Usuario, "100521347")

    assert guardado is not None
    assert guardado.rol == Rol.DOCENTE
    assert guardado.activo is True
    assert guardado.creado_en is not None
    assert guardado.nombre_completo == "Laura Méndez Ortega"


def test_email_repetido_se_rechaza(sesion: Session) -> None:
    sesion.add(nuevo_usuario(usuario="100521347"))
    sesion.commit()

    sesion.add(nuevo_usuario(usuario="100534812"))  # otro usuario, mismo email
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_usuario_de_mas_de_9_caracteres_se_rechaza(sesion: Session) -> None:
    # SQLite aceptaría este valor; PostgreSQL respeta el String(9).
    sesion.add(nuevo_usuario(usuario="1005213470"))
    with pytest.raises(DataError):
        sesion.commit()
