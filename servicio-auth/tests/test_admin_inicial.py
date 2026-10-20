import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.contrasenas import verificar_contrasena
from app.modelos import Usuario
from app.servicios.admin_inicial import crear_admin_inicial
from schooldesk_comun.roles import Rol
from tests.fabricas import nuevo_usuario


def contar_admins(sesion: Session) -> int:
    return sesion.scalar(select(func.count()).where(Usuario.rol == Rol.ADMIN))


def test_en_una_base_vacia_crea_el_admin(sesion: Session) -> None:
    assert crear_admin_inicial(sesion, "100500001", "contrasena-del-admin") is True

    admin = sesion.get(Usuario, "100500001")
    assert admin.rol == Rol.ADMIN
    assert verificar_contrasena("contrasena-del-admin", admin.hash_contrasena)


def test_reiniciar_el_servicio_no_crea_otro(sesion: Session) -> None:
    crear_admin_inicial(sesion, "100500001", "contrasena-del-admin")

    assert crear_admin_inicial(sesion, "100500001", "contrasena-del-admin") is False
    assert contar_admins(sesion) == 1


def test_si_ya_hay_otro_admin_no_hace_nada(sesion: Session) -> None:
    sesion.add(nuevo_usuario(usuario="100599999", email="otro@example.com", rol=Rol.ADMIN))
    sesion.commit()

    assert crear_admin_inicial(sesion, "100500001", "contrasena-del-admin") is False
    assert sesion.get(Usuario, "100500001") is None


@pytest.mark.parametrize(
    ("usuario", "contrasena"), [("admin", "contrasena-del-admin"), ("100500001", "corta")]
)
def test_datos_invalidos_detienen_el_arranque(
    sesion: Session, usuario: str, contrasena: str
) -> None:
    with pytest.raises(ValueError):
        crear_admin_inicial(sesion, usuario, contrasena)
