"""Carga los datos de la demo usando la API (a través del gateway), como lo haría el frontend.

No escribe directo en las bases de datos: así pasa por las mismas validaciones
que el uso real (importación CSV, pesos que suman 100, QR de un solo uso...).

Uso, con el backend levantado (docker compose up -d), desde la raíz del backend:
    .venv/Scripts/python semilla/sembrar.py

Se puede correr varias veces: las importaciones omiten lo que ya existe y los
pasos de calificaciones y asistencia se saltan si ya hay datos.

Sobre las calificaciones: se generan con random.Random(SEMILLA), que siempre da
la misma secuencia, así que la demo es reproducible. Y se GUARDAN en la base
como cualquier captura; nada se inventa en la pantalla al mostrarse.
"""

import random
import sys
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos-ejemplo"
URL_GATEWAY = "http://localhost:8000"

NRC_DEMO = "48308"  # Desarrollo de Sitios Web, la imparte Laura Méndez
DOCENTE_DEMO = "100521347"
SEMILLA = 48308

# Ponderaciones de la materia de la demo: categoría → (peso, tareas).
# Parcial 2 y el Proyecto quedan SIN calificar a propósito, para mostrar el
# "promedio actual" (las categorías sin calificaciones no cuentan todavía).
PONDERACIONES = {
    "Prácticas": (40, ["Práctica 1: HTML semántico", "Práctica 2: CSS Grid", "Práctica 3: Blog de café"]),
    "Exámenes": (40, ["Parcial 1", "Parcial 2"]),
    "Proyecto": (20, ["Proyecto final"]),
}
SIN_CALIFICAR = {"Parcial 2", "Proyecto final"}
SESIONES_DE_ASISTENCIA = 3


def main() -> None:
    # La consola de Windows usa cp1252 por defecto y no puede imprimir → ni ✓.
    sys.stdout.reconfigure(encoding="utf-8")
    entorno = leer_env(RAIZ / ".env")
    api = httpx.Client(base_url=URL_GATEWAY, timeout=120)

    paso("Revisando que el backend esté arriba")
    estados = pedir(api, "GET", "/salud/servicios")
    if set(estados.values()) != {"ok"}:
        detener(f"Algún servicio no responde: {estados}. ¿Corriste docker compose up -d?")

    paso("Entrando como el admin inicial")
    admin = iniciar_sesion(api, entorno["ADMIN_INICIAL_USUARIO"], entorno["ADMIN_INICIAL_CONTRASENA"])

    # El orden importa: las materias necesitan a los docentes y las
    # inscripciones necesitan alumnos y materias.
    for servicio, tipo in [
        ("auth", "docentes"),
        ("academico", "alumnos"),
        ("academico", "materias"),
        ("academico", "inscripciones"),
    ]:
        paso(f"Importando {tipo}.csv")
        resultado = importar(api, admin, servicio, tipo)
        print(f"   creados: {resultado['creados']}, omitidos: {len(resultado['omitidos'])}")

    # El docente entra con su contraseña inicial (su número de empleado).
    docente = iniciar_sesion(api, DOCENTE_DEMO, DOCENTE_DEMO)
    rng = random.Random(SEMILLA)

    paso(f"Ponderaciones y calificaciones de la materia {NRC_DEMO}")
    if pedir(api, "GET", f"/api/academico/materias/{NRC_DEMO}/categorias", headers=docente):
        print("   ya tenía ponderaciones: se omite")
    else:
        sembrar_calificaciones(api, docente, rng)

    paso(f"Sesiones de asistencia de la materia {NRC_DEMO}")
    if pedir(api, "GET", "/api/asistencia/sesiones", headers=docente, params={"nrc": NRC_DEMO}):
        print("   ya tenía sesiones: se omite")
    else:
        sembrar_asistencia(api, docente, rng)

    imprimir_credenciales(entorno)


# --- Pasos ---


def sembrar_calificaciones(api: httpx.Client, docente: dict[str, str], rng: random.Random) -> None:
    categorias = pedir(
        api,
        "PUT",
        f"/api/academico/materias/{NRC_DEMO}/categorias",
        headers=docente,
        json=[{"nombre": nombre, "peso": peso} for nombre, (peso, _) in PONDERACIONES.items()],
    )
    tareas_a_calificar = []
    for categoria in categorias:
        for nombre_tarea in PONDERACIONES[categoria["nombre"]][1]:
            tarea = pedir(
                api,
                "POST",
                f"/api/academico/materias/{NRC_DEMO}/categorias/{categoria['id']}/tareas",
                headers=docente,
                json={"nombre": nombre_tarea},
            )
            if nombre_tarea not in SIN_CALIFICAR:
                tareas_a_calificar.append(tarea["id"])

    alumnos = pedir(api, "GET", f"/api/academico/materias/{NRC_DEMO}/alumnos", headers=docente)
    entradas = []
    for alumno in alumnos:
        # Cada alumno tiene un "nivel" y sus calificaciones varían alrededor de él,
        # así hay alumnos destacados, regulares y algunos reprobados.
        nivel = rng.randint(45, 98)
        for tarea_id in tareas_a_calificar:
            no_entrego = rng.random() < 0.05
            puntos = 0 if no_entrego else max(0, min(100, nivel + rng.randint(-12, 12)))
            entradas.append({"matricula": alumno["matricula"], "tarea_id": tarea_id, "puntos": puntos})

    pedir(api, "PUT", f"/api/academico/materias/{NRC_DEMO}/calificaciones", headers=docente, json=entradas)
    print(f"   {len(categorias)} categorías, {len(entradas)} calificaciones capturadas")


def sembrar_asistencia(api: httpx.Client, docente: dict[str, str], rng: random.Random) -> None:
    """Sesiones reales: el docente abre, cada alumno genera su QR, el docente escanea y cierra."""
    alumnos = pedir(api, "GET", f"/api/academico/materias/{NRC_DEMO}/alumnos", headers=docente)
    # Cada alumno entra con su contraseña inicial (su matrícula) para pedir su QR.
    tokens = {a["matricula"]: iniciar_sesion(api, a["matricula"], a["matricula"]) for a in alumnos}

    for numero in range(1, SESIONES_DE_ASISTENCIA + 1):
        sesion = pedir(api, "POST", "/api/asistencia/sesiones", headers=docente, json={"nrc": NRC_DEMO})
        asistentes = [m for m in tokens if rng.random() > 0.12]  # ~88 % de asistencia
        for matricula in asistentes:
            qr = pedir(api, "POST", "/api/asistencia/qr", headers=tokens[matricula], json={"nrc": NRC_DEMO})
            pedir(
                api,
                "POST",
                f"/api/asistencia/sesiones/{sesion['id']}/escanear",
                headers=docente,
                json={"token": qr["token"]},
            )
        pedir(api, "POST", f"/api/asistencia/sesiones/{sesion['id']}/cerrar", headers=docente)
        print(f"   sesión {numero}: {len(asistentes)} de {len(alumnos)} asistieron")


# --- Ayudantes ---


def iniciar_sesion(api: httpx.Client, usuario: str, contrasena: str) -> dict[str, str]:
    respuesta = pedir(api, "POST", "/api/auth/login", json={"usuario": usuario, "contrasena": contrasena})
    return {"Authorization": f"Bearer {respuesta['token_acceso']}"}


def importar(api: httpx.Client, admin: dict[str, str], servicio: str, tipo: str) -> dict:
    archivo = DATOS / f"{tipo}.csv"
    return pedir(
        api,
        "POST",
        f"/api/{servicio}/importar/{tipo}",
        headers=admin,
        files={"archivo": (archivo.name, archivo.read_bytes(), "text/csv")},
    )


def pedir(api: httpx.Client, metodo: str, ruta: str, **opciones: object) -> dict | list:
    """Hace la petición y se detiene con un mensaje claro si la API responde con error."""
    try:
        respuesta = api.request(metodo, ruta, **opciones)
    except httpx.ConnectError:
        detener(f"No hay conexión con {URL_GATEWAY}. ¿Corriste docker compose up -d?")
    if not respuesta.is_success:
        detener(f"{metodo} {ruta} respondió {respuesta.status_code}: {respuesta.text}")
    return respuesta.json() if respuesta.content else {}


def leer_env(ruta: Path) -> dict[str, str]:
    if not ruta.exists():
        detener("No existe .env: copia .env.example como .env y cambia las claves")
    lineas = (linea.strip() for linea in ruta.read_text(encoding="utf-8").splitlines())
    return dict(linea.split("=", 1) for linea in lineas if linea and not linea.startswith("#"))


def paso(texto: str) -> None:
    print(f"\n→ {texto}")


def detener(mensaje: str) -> None:
    print(f"\n✗ {mensaje}")
    sys.exit(1)


def imprimir_credenciales(entorno: dict[str, str]) -> None:
    print("\n✓ Listo. Usuarios para la demo (la contraseña inicial es el mismo número):")
    print(f"   Admin:   {entorno['ADMIN_INICIAL_USUARIO']}  (contraseña: ADMIN_INICIAL_CONTRASENA de .env)")
    print(f"   Docente: {DOCENTE_DEMO}  Laura Méndez Ortega, imparte {NRC_DEMO} y 50130")
    print("   Alumna:  202231045  Ana Sofía Acosta Bravo")


if __name__ == "__main__":
    main()
