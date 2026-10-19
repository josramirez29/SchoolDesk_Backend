# SchoolDesk — Backend

Sistema escolar con 3 microservicios (FastAPI + SQLAlchemy + PostgreSQL), un API Gateway y Redis.

> Este sistema se encuentra en construcción. La documentación completa (arquitectura, decisiones y cómo correrlo) se agregará al final.

## Estructura

```
comun/                Código común: roles, validación de JWT, formato de errores
gateway/              Punto de entrada único (/api/{servicio}/...)
servicio-auth/        Usuarios, login y emisión de JWT
servicio-academico/   Materias, alumnos, inscripciones, calificaciones y reportes
servicio-asistencia/  Sesiones de asistencia con QR dinámico (Redis)
datos-ejemplo/        CSV de ejemplo para la importación masiva
```
