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
