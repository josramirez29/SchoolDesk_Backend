# servicio-asistencia

Sesiones de asistencia de 10 minutos con QR dinámico. El docente abre la
sesión, el alumno genera un QR de un solo uso y el docente lo escanea:
dentro de los primeros 5 minutos queda PRESENTE; después, RETARDO.

- **PostgreSQL** guarda el historial: sesiones y registros.
- **Redis** guarda los tokens de QR, que duran 30 segundos y se usan una vez.

## Correr las pruebas

Requisitos: Python 3.12 y **Docker encendido**. Las pruebas levantan su propio
PostgreSQL y Redis en contenedores temporales (testcontainers).

Desde esta carpeta (`servicio-asistencia/`):

```bash
pip install -e ../comun -r requirements-pruebas.txt
pytest
```
