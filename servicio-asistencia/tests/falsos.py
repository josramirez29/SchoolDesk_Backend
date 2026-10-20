"""Versiones falsas de lo que el servicio usa de fuera: academic y el reloj."""

from datetime import datetime, timedelta

from app.clientes.academico import AlumnoInscrito, ClienteAcademico, MateriaAcademica
from schooldesk_comun.errores import ErrorApp
from tests.fabricas import INICIO_CLASE


class ClienteAcademicoFalso(ClienteAcademico):
    """Academic simulado con los datos de datos-ejemplo/ (Laura da Sitios Web)."""

    def __init__(self) -> None:  # no llama a super(): no necesita conexión HTTP
        self.materias = {
            "48308": MateriaAcademica(
                nrc="48308", nombre="Desarrollo de Sitios Web", num_empleado_docente="100521347"
            ),
        }
        self.inscritos = {
            ("48308", "202231045"): AlumnoInscrito(
                matricula="202231045", nombre="Ana Sofía", apellidos="Acosta Bravo"
            ),
            ("48308", "202233918"): AlumnoInscrito(
                matricula="202233918", nombre="Bruno", apellidos="Aguilar Campos"
            ),
        }
        self.error: ErrorApp | None = None  # si se asigna, cada llamada lo lanza

    def obtener_materia(self, nrc: str) -> MateriaAcademica:
        self._fallar_si_se_pidio()
        if nrc not in self.materias:
            raise ErrorApp(404, "MATERIA_NO_ENCONTRADA", f"No existe la materia con NRC {nrc}")
        return self.materias[nrc]

    def obtener_alumno_inscrito(self, nrc: str, matricula: str) -> AlumnoInscrito:
        self._fallar_si_se_pidio()
        if (nrc, matricula) not in self.inscritos:
            raise ErrorApp(404, "NO_INSCRITO", f"El alumno {matricula} no está inscrito")
        return self.inscritos[(nrc, matricula)]

    def _fallar_si_se_pidio(self) -> None:
        if self.error is not None:
            raise self.error


class RelojFalso:
    """Reloj que las pruebas mueven a voluntad: empieza a las 9:00 de la clase."""

    def __init__(self) -> None:
        self.ahora: datetime = INICIO_CLASE

    def avanzar(self, minutos: float) -> None:
        self.ahora += timedelta(minutes=minutos)
