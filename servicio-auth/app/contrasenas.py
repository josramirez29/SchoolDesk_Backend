from concurrent.futures import ThreadPoolExecutor

import bcrypt


def generar_hash(contrasena: str) -> str:
    """Convierte la contraseña en un hash bcrypt (incluye una sal aleatoria).

    Nunca se guarda la contraseña original: si alguien roba la base de datos,
    solo obtiene hashes, que no se pueden revertir.
    """
    return bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(contrasena.encode(), hash_guardado.encode())


# Hash de una contraseña que nadie usa. Sirve para que el login tarde lo mismo
# cuando el usuario no existe (ver servicios/autenticacion.py).
HASH_FALSO = generar_hash("contrasena-que-nadie-usa")


def generar_hashes(contrasenas: list[str]) -> list[str]:
    """Genera muchos hashes en paralelo (para la importación masiva).

    bcrypt tarda ~0.25 s por contraseña a propósito, para frenar ataques de
    fuerza bruta. Uno tras otro, 150 docentes tardarían casi 40 s. bcrypt libera
    el GIL mientras calcula, así que con hilos sí se usan todos los núcleos.
    """
    with ThreadPoolExecutor() as ejecutor:
        return list(ejecutor.map(generar_hash, contrasenas))
