# servicio-auth

Usuarios, login y emisión de JWT. Es el único servicio que **firma** tokens;
los demás solo los validan con la clave compartida.

## Correr las pruebas

Requisitos: Python 3.12 y **Docker encendido**. Las pruebas levantan su propio
PostgreSQL en un contenedor temporal (testcontainers), así que no necesitas
crear ninguna base de datos.

Desde esta carpeta (`servicio-auth/`):

```bash
pip install -e ../comun -r requirements-pruebas.txt
pytest
```
