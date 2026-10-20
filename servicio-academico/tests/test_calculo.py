"""Pruebas del cálculo del promedio. No usan base de datos: son instantáneas."""

from decimal import Decimal

from app.calculo import CategoriaParaCalculo, calcular_promedios, promedio_final

D = Decimal

PRACTICAS = CategoriaParaCalculo(id=1, peso=D("40"), tarea_ids=[10, 11])
EXAMENES = CategoriaParaCalculo(id=2, peso=D("60"), tarea_ids=[20])
PROYECTO = CategoriaParaCalculo(id=3, peso=D("20"), tarea_ids=[30])


def test_ejemplo_del_diseno() -> None:
    # Prácticas 40 % (100 y 80 → 90), Exámenes 60 % (80): (90×40 + 80×60) / 100 = 84 → 8.4
    promedios = calcular_promedios([PRACTICAS, EXAMENES], {10: D("100"), 11: D("80"), 20: D("80")})

    assert promedios.por_categoria == {1: D("90.00"), 2: D("80.00")}
    assert promedios.final == D("8.4")


def test_tareas_sin_calificar_no_cuentan_en_su_categoria() -> None:
    # Solo la tarea 10 está calificada: el promedio de Prácticas es 100, no 50.
    promedios = calcular_promedios([PRACTICAS], {10: D("100")})

    assert promedios.por_categoria[1] == D("100.00")
    assert promedios.final == D("10.0")


def test_categoria_sin_calificaciones_no_baja_el_promedio_actual() -> None:
    # A mitad de semestre: Exámenes aún no se califica. El promedio actual
    # es 10, no 4 (que es lo que daría contar Exámenes como 0).
    promedios = calcular_promedios([PRACTICAS, EXAMENES], {10: D("100"), 11: D("100")})

    assert promedios.por_categoria[2] is None
    assert promedios.final == D("10.0")


def test_sin_ninguna_calificacion_no_hay_promedio() -> None:
    promedios = calcular_promedios([PRACTICAS, EXAMENES, PROYECTO], {})

    assert promedios.final is None
    assert promedios.por_categoria == {1: None, 2: None, 3: None}


def test_redondea_hacia_arriba_en_el_medio() -> None:
    # 84.5 / 10 = 8.45 → 8.5 (redondeo escolar, no al par más cercano).
    assert promedio_final([(D("100"), D("84.5"))]) == D("8.5")


def test_el_resultado_es_exacto_con_decimales() -> None:
    # Con float, 3 tareas de 70, 80 y 90.1 pueden dar 80.03333333333333.
    promedios = calcular_promedios(
        [CategoriaParaCalculo(id=1, peso=D("100"), tarea_ids=[1, 2, 3])],
        {1: D("70"), 2: D("80"), 3: D("90.1")},
    )

    assert promedios.por_categoria[1] == D("80.03")
    assert promedios.final == D("8.0")
