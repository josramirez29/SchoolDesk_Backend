# servicio-academico

Núcleo del dominio: alumnos, materias, inscripciones, ponderaciones por
categorías, calificaciones, promedio ponderado y reporte de materia.

## Correr las pruebas

Requisitos: Python 3.12 y **Docker encendido**. Las pruebas levantan su propio
PostgreSQL en un contenedor temporal (testcontainers).

Desde esta carpeta (`servicio-academico/`):

```bash
pip install -e ../comun -r requirements-pruebas.txt
pytest
```
