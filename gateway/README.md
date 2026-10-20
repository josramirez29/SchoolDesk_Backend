# gateway

Punto de entrada único del backend. Solo enruta; no tiene lógica de negocio
ni valida el JWT (eso lo hace cada servicio).

| Ruta | Servicio |
|---|---|
| `/api/auth/...` | servicio-auth |
| `/api/academico/...` | servicio-academico |
| `/api/asistencia/...` | servicio-asistencia |

Además: CORS para el frontend, bloqueo de `/interno/*`, 503/504 si un servicio
no responde y `GET /salud/servicios` para ver el estado de los tres.

## Correr las pruebas

```bash
pip install -e ../comun -r requirements.txt
pytest
```
