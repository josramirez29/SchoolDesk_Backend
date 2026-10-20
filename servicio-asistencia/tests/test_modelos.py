import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos import EstadoAsistencia, Registro
from tests.fabricas import minutos_despues, nueva_sesion

# --- Reglas de tiempo (sin base de datos) ---


def test_la_sesion_esta_activa_durante_sus_10_minutos() -> None:
    sesion = nueva_sesion()

    assert sesion.esta_activa(minutos_despues(0))
    assert sesion.esta_activa(minutos_despues(9.9))
    assert not sesion.esta_activa(minutos_despues(10))


def test_una_sesion_cerrada_antes_ya_no_esta_activa() -> None:
    sesion = nueva_sesion(cerrada_en=minutos_despues(3))

    assert not sesion.esta_activa(minutos_despues(4))


def test_segundos_restantes() -> None:
    sesion = nueva_sesion()

    assert sesion.segundos_restantes(minutos_despues(7.5)) == 150
    assert sesion.segundos_restantes(minutos_despues(12)) == 0


@pytest.mark.parametrize(
    ("minuto", "estado"),
    [
        (0, EstadoAsistencia.PRESENTE),
        (5, EstadoAsistencia.PRESENTE),  # justo en el límite todavía es PRESENTE
        (5.02, EstadoAsistencia.RETARDO),
        (9.9, EstadoAsistencia.RETARDO),
    ],
)
def test_presente_hasta_los_5_minutos_y_despues_retardo(minuto: float, estado: EstadoAsistencia) -> None:
    assert nueva_sesion().estado_para(minutos_despues(minuto), minutos_tolerancia=5) == estado


# --- Base de datos ---


def test_un_alumno_no_puede_registrarse_dos_veces_en_la_misma_sesion(bd: Session) -> None:
    sesion = nueva_sesion()
    bd.add(sesion)
    bd.flush()

    def registro() -> Registro:
        return Registro(
            sesion_id=sesion.id,
            matricula="202231045",
            nombre_alumno="Ana Sofía Acosta Bravo",
            estado=EstadoAsistencia.PRESENTE,
            registrado_en=minutos_despues(1),
        )

    bd.add(registro())
    bd.commit()

    bd.add(registro())
    with pytest.raises(IntegrityError):
        bd.commit()


def test_registros_se_ordenan_por_hora_de_llegada(bd: Session) -> None:
    sesion = nueva_sesion()
    sesion.registros.extend(
        [
            Registro(
                matricula="202233918",
                nombre_alumno="Bruno Aguilar Campos",
                estado=EstadoAsistencia.RETARDO,
                registrado_en=minutos_despues(6),
            ),
            Registro(
                matricula="202231045",
                nombre_alumno="Ana Sofía Acosta Bravo",
                estado=EstadoAsistencia.PRESENTE,
                registrado_en=minutos_despues(1),
            ),
        ]
    )
    bd.add(sesion)
    bd.commit()
    bd.expire_all()  # vuelve a leer de la base, con el orden de la relación

    assert [r.matricula for r in sesion.registros] == ["202231045", "202233918"]
