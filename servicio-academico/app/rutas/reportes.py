"""Ruta del reporte de materia (admin o docente titular)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.base_datos import obtener_sesion
from app.clientes.asistencia import ClienteAsistencia
from app.dependencias import admin_o_docente, obtener_cliente_asistencia
from app.esquemas import ReporteMateria
from app.servicios import reportes
from schooldesk_comun.seguridad import UsuarioActual

router = APIRouter(prefix="/materias/{nrc}/reporte", tags=["Reportes"])


@router.get("", response_model=ReporteMateria)
def reporte(
    nrc: str,
    usuario: UsuarioActual = Depends(admin_o_docente),
    sesion: Session = Depends(obtener_sesion),
    cliente_asistencia: ClienteAsistencia = Depends(obtener_cliente_asistencia),
) -> ReporteMateria:
    return reportes.generar_reporte(sesion, cliente_asistencia, nrc, usuario)
