"""Cálculo del promedio ponderado. Funciones puras: sin base de datos ni HTTP.

Reglas (opción B, aprobada):
1. Promedio de una categoría = promedio de los puntos (0–100) de sus tareas CALIFICADAS.
   Las tareas sin calificar no cuentan.
2. Promedio ponderado = Σ(promedio de categoría × peso) / Σ(pesos de las categorías
   que ya tienen calificaciones). Así, a mitad de semestre es el "promedio actual".
3. Calificación final = promedio ponderado / 10, en escala 0–10 con un decimal.

Ejemplo: Prácticas 40 % con promedio 90, Exámenes 60 % con 80, Proyecto sin calificar:
    (90 × 40 + 80 × 60) / (40 + 60) = 84  →  8.4
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

UN_DECIMAL = Decimal("0.1")
DOS_DECIMALES = Decimal("0.01")


@dataclass(frozen=True)
class CategoriaParaCalculo:
    id: int
    peso: Decimal
    tarea_ids: list[int]


@dataclass(frozen=True)
class Promedios:
    por_categoria: dict[int, Decimal | None]  # 0–100, None si no tiene calificaciones
    final: Decimal | None  # 0–10, None si el alumno no tiene ninguna calificación


def calcular_promedios(
    categorias: list[CategoriaParaCalculo], puntos_por_tarea: dict[int, Decimal]
) -> Promedios:
    """Promedios de UN alumno. `puntos_por_tarea` solo trae las tareas calificadas."""
    por_categoria = {
        categoria.id: promedio_de_categoria(
            [puntos_por_tarea[t] for t in categoria.tarea_ids if t in puntos_por_tarea]
        )
        for categoria in categorias
    }

    con_calificaciones = [
        (categoria.peso, por_categoria[categoria.id])
        for categoria in categorias
        if por_categoria[categoria.id] is not None
    ]
    return Promedios(por_categoria=por_categoria, final=promedio_final(con_calificaciones))


def promedio_de_categoria(puntos: list[Decimal]) -> Decimal | None:
    # Se redondea a 2 decimales y el final se calcula con ese valor redondeado:
    # así cualquiera puede rehacer la cuenta con los números que ve en pantalla.
    if not puntos:
        return None
    return (sum(puntos, Decimal("0")) / len(puntos)).quantize(DOS_DECIMALES, ROUND_HALF_UP)


def promedio_final(pesos_y_promedios: list[tuple[Decimal, Decimal]]) -> Decimal | None:
    if not pesos_y_promedios:
        return None
    suma_pesos = sum((peso for peso, _ in pesos_y_promedios), Decimal("0"))
    ponderado = sum((peso * promedio for peso, promedio in pesos_y_promedios), Decimal("0"))
    # ROUND_HALF_UP: 8.45 → 8.5, como se redondea en la escuela.
    # (Python redondea por defecto al par más cercano: round(8.45, 1) puede dar 8.4.)
    return (ponderado / suma_pesos / 10).quantize(UN_DECIMAL, ROUND_HALF_UP)


# --- Asistencia y resumen del grupo (para el reporte de materia) ---

CALIFICACION_APROBATORIA = Decimal("6")  # escala BUAP: 6 o más aprueba


@dataclass(frozen=True)
class Asistencia:
    presentes: int
    retardos: int
    faltas: int
    porcentaje: Decimal | None  # None si todavía no hay sesiones


def calcular_asistencia(total_sesiones: int, presentes: int, retardos: int) -> Asistencia:
    """Un retardo cuenta como asistencia (el alumno sí llegó); solo las faltas restan."""
    faltas = max(total_sesiones - presentes - retardos, 0)
    porcentaje = None
    if total_sesiones > 0:
        porcentaje = (Decimal(presentes + retardos) * 100 / total_sesiones).quantize(
            UN_DECIMAL, ROUND_HALF_UP
        )
    return Asistencia(presentes=presentes, retardos=retardos, faltas=faltas, porcentaje=porcentaje)


@dataclass(frozen=True)
class ResumenGrupo:
    promedio_grupo: Decimal | None
    aprobados: int
    reprobados: int
    sin_calificaciones: int


def resumir_grupo(promedios: list[Decimal | None]) -> ResumenGrupo:
    calificados = [promedio for promedio in promedios if promedio is not None]
    promedio_grupo = None
    if calificados:
        promedio_grupo = (sum(calificados, Decimal("0")) / len(calificados)).quantize(
            UN_DECIMAL, ROUND_HALF_UP
        )
    aprobados = sum(1 for promedio in calificados if promedio >= CALIFICACION_APROBATORIA)
    return ResumenGrupo(
        promedio_grupo=promedio_grupo,
        aprobados=aprobados,
        reprobados=len(calificados) - aprobados,
        sin_calificaciones=len(promedios) - len(calificados),
    )
