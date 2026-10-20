# SchoolDesk - Backend

Sistema escolar para administrar alumnos, materias, calificaciones y
asistencia con QR dinámico. Está construido con 3 microservicios en FastAPI, un
API Gateway, PostgreSQL y Redis, y se levanta completo con un solo comando.

Frontend (Angular): https://github.com/josramirez29/SchoolDesk_Frontend


## Arquitectura

El frontend solo habla con el gateway (puerto 8000), y el gateway reenvía cada
petición al servicio que le corresponde:

- /api/auth/... va a servicio-auth
- /api/academico/... va a servicio-academico
- /api/asistencia/... va a servicio-asistencia

Cada servicio tiene su propia base de datos en PostgreSQL (auth_db, academico_db
y asistencia_db). Además, servicio-asistencia usa Redis para los tokens de QR.

Los servicios se llaman entre sí por HTTP en estos casos:

- academico llama a auth para crear las cuentas de los alumnos y para validar
  que el docente de una materia exista.
- academico llama a asistencia para obtener el resumen de asistencia del reporte.
- asistencia llama a academico para saber quién es el titular de una materia y
  si un alumno está inscrito.

Qué hace cada parte y por qué va separada:

- servicio-auth: usuarios, login, emisión de JWT y roles. Va separado porque la
  identidad es reutilizable y concentra lo sensible (las contraseñas).
- servicio-academico: alumnos, materias, inscripciones, ponderaciones,
  calificaciones, promedios y reporte. Es el núcleo del dominio; sus datos
  cambian juntos, así que van juntos.
- servicio-asistencia: sesiones de 10 minutos, QR de un solo uso y registro de
  asistencia. Tiene otra carga (picos al inicio de cada clase) y otra tecnología
  (Redis, datos que expiran).
- gateway: punto de entrada único, CORS y bloqueo de rutas internas. El frontend
  conoce una sola URL y los servicios no se exponen.
- comun: roles, validación de JWT, formato de errores, tipos, lector de CSV y
  cliente entre servicios. Lo que debe ser idéntico en todos los servicios se
  escribe una sola vez.

Comunicación: HTTP síncrono entre servicios, sin broker de mensajes. Con 3
servicios y pocas interacciones, HTTP basta; si hubiera flujos asíncronos (por
ejemplo, notificaciones por correo), agregaría una cola.


## Cómo correrlo

Requisitos: Docker Desktop. Python 3.12 solo hace falta para la semilla y las pruebas.

1. Copia el archivo de configuración de ejemplo y cambia las claves:

```bash
cp .env.example .env
```

2. Levanta todo (PostgreSQL, Redis, los 3 servicios y el gateway):

```bash
docker compose up --build -d
```

3. Carga los datos de ejemplo (se cargan a través de la API):

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install httpx
.venv/Scripts/python semilla/sembrar.py
```

En Linux o macOS, usa "python3.12 -m venv .venv" y ".venv/bin/python".

Direcciones:

- http://localhost:8000 - gateway, lo único que usa el frontend
- http://localhost:8000/salud/servicios - estado de los 3 servicios
- http://localhost:8001/docs - Swagger de servicio-auth (solo en desarrollo)
- http://localhost:8002/docs - Swagger de servicio-academico
- http://localhost:8003/docs - Swagger de servicio-asistencia

Usuarios de ejemplo (la contraseña inicial es el mismo número y cada quien puede
cambiarla):

- Admin: el usuario y la contraseña de ADMIN_INICIAL_USUARIO y
  ADMIN_INICIAL_CONTRASENA en el archivo .env
- Docente: 100521347 (Laura Méndez Ortega, imparte 48308 y 50130)
- Alumna: 202231045 (Ana Sofía Acosta Bravo)

Comandos útiles:

```bash
docker compose logs -f servicio-academico
docker compose down
docker compose down -v
```

El primero muestra los logs de un servicio, el segundo detiene todo y el tercero
detiene todo y además borra los datos.

## Pruebas

Son 233 pruebas con pytest, contra PostgreSQL y Redis reales en contenedores
temporales (testcontainers). Las llamadas a otros servicios se reemplazan por
clientes falsos inyectados.

- comun: 26
- servicio-auth: 47
- servicio-academico: 97
- servicio-asistencia: 47
- gateway: 16

Instalación (una vez, desde la raíz del backend):

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -e ./comun -r servicio-auth/requirements-pruebas.txt -r servicio-academico/requirements-pruebas.txt -r servicio-asistencia/requirements-pruebas.txt -r gateway/requirements-pruebas.txt -r requirements-desarrollo.txt
```

Para correr las pruebas de un paquete, desde su carpeta y con Docker encendido:

```bash
../.venv/Scripts/python -m pytest
```

Formato y revisión de código, desde la raíz:

```bash
.venv/Scripts/ruff format .
.venv/Scripts/ruff check .
```


## API

Todas las rutas pasan por el gateway con el prefijo del servicio, por ejemplo
POST /api/auth/login o GET /api/academico/materias. Los errores siempre tienen
el mismo formato: {"error": "CODIGO", "detalle": "mensaje legible"}.

Rutas principales:

- /api/auth: POST /login, GET /perfil, PUT /perfil/contrasena, /usuarios (admin)
  y /importar/docentes.
- /api/academico: /alumnos, /materias, /materias/{nrc}/alumnos,
  /materias/{nrc}/categorias, /materias/{nrc}/calificaciones,
  /materias/{nrc}/reporte, /mis-materias e /importar/alumnos, /importar/materias
  e /importar/inscripciones.
- /api/asistencia: /sesiones, /sesiones/{id}/escanear, /sesiones/{id}/cerrar,
  POST /qr y /mi-asistencia.

La documentación completa de cada endpoint está en el Swagger de cada servicio
(ver la sección "Cómo correrlo").


## Estructura del repositorio

```
comun/                Paquete compartido: roles, JWT, errores, tipos, CSV, cliente interno
gateway/              Punto de entrada único (asíncrono)
servicio-auth/        app/ (rutas, servicios y modelos) y tests/
servicio-academico/   igual, más calculo.py (promedios) y clientes/ hacia auth y asistencia
servicio-asistencia/  igual, más redis_cliente.py y reloj.py
datos-ejemplo/        CSV para la importación (materias reales de ITI; personas ficticias)
semilla/              sembrar.py: carga los datos de ejemplo usando la API
docker/               script que crea las 3 bases en PostgreSQL
docker-compose.yml    los 6 contenedores y su orden de arranque
```

En cada servicio, las rutas solo reciben la petición y responden, los servicios
tienen la lógica y los modelos son las tablas. Así la lógica se puede probar y
reutilizar sin pasar por HTTP.
